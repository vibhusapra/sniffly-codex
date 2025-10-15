"""
Utility helpers for locating Claude and Codex CLI log directories.
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CODEX_SLUG_PREFIX = "codex~"


def _claude_base() -> Path:
    return Path.home() / ".claude" / "projects"


def _codex_base() -> Path:
    return Path.home() / ".codex" / "sessions"


def find_claude_logs(project_path: str) -> str | None:
    """
    Find Claude logs for a given project path.

    Claude stores logs at ~/.claude/projects/[converted-project-path]/
    where the project path has slashes replaced with dashes and starts with a dash.

    Example:
        /Users/john/dev/myapp -> ~/.claude/projects/-Users-john-dev-myapp/

    Args:
        project_path: The project directory path

    Returns:
        Path to Claude logs directory if found, None otherwise
    """
    # Normalize the project path
    project_path = os.path.abspath(project_path)

    # Remove trailing slash if present
    if project_path.endswith("/"):
        project_path = project_path[:-1]

    # Convert to Claude log format
    converted_path = project_path.replace("/", "-")

    # Construct the Claude log path
    claude_base = _claude_base()
    log_path = claude_base / converted_path

    # Check if it exists
    if log_path.exists() and log_path.is_dir():
        jsonl_files = list(log_path.glob("*.jsonl"))
        if jsonl_files:
            return str(log_path)

    # Try without leading dash (older format)
    if converted_path.startswith("-"):
        alt_path = claude_base / converted_path[1:]
        if alt_path.exists() and alt_path.is_dir():
            jsonl_files = list(alt_path.glob("*.jsonl"))
            if jsonl_files:
                return str(alt_path)

    return None


def list_all_claude_projects() -> list:
    """
    List all Claude projects found on the system.

    Returns:
        List of tuples (project_path, log_path)
    """
    projects = []
    claude_base = _claude_base()

    if not claude_base.exists():
        return projects

    for log_dir in claude_base.iterdir():
        if log_dir.is_dir():
            dir_name = log_dir.name

            # Handle leading dash
            if dir_name.startswith("-"):
                project_path = "/" + dir_name[1:].replace("-", "/")
            else:
                project_path = dir_name.replace("-", "/")

            jsonl_files = list(log_dir.glob("*.jsonl"))
            if jsonl_files:
                projects.append((project_path, str(log_dir)))

    return projects


def validate_project_path(project_path: str) -> tuple[bool, str]:
    """
    Validate a project path and return status with message.

    Returns:
        (is_valid, message)
    """
    if not project_path:
        return False, "Project path cannot be empty"

    if not os.path.exists(project_path):
        return False, f"Project path does not exist: {project_path}"

    if not os.path.isdir(project_path):
        return False, f"Project path must be a directory: {project_path}"

    # Check if logs exist
    log_path = find_claude_logs(project_path)
    if not log_path:
        return False, f"No Claude logs found for project: {project_path}"

    return True, f"Found logs at: {log_path}"


def slugify_log_path(log_path: str) -> str:
    """
    Convert an absolute log path into a URL-safe slug that can be used
    to reference the project from the UI or API.
    """
    path = Path(log_path)

    try:
        relative = path.relative_to(_claude_base())
        # Claude project directories are already flattened, but replace any slashes just in case.
        return relative.as_posix().replace("/", "~")
    except ValueError:
        pass

    try:
        relative = path.relative_to(_codex_base())
        parts = [part for part in relative.parts if part]
        if parts:
            return CODEX_SLUG_PREFIX + "~".join(parts)
    except ValueError:
        pass

    return path.name


def describe_log_path(log_path: str) -> dict[str, Any]:
    """
    Produce descriptive metadata for a log directory.

    Returns:
        {
            'log_path': absolute path string,
            'dir_name': slug used in URLs,
            'display_name': human friendly label,
            'provider': 'claude' | 'codex' | 'unknown'
        }
    """
    path = Path(log_path)
    slug = slugify_log_path(log_path)
    provider = "unknown"
    display_name = slug

    try:
        relative = path.relative_to(_claude_base())
        provider = "claude"
        if "~" in slug:
            display_name = slug.replace("~", "/")
    except ValueError:
        try:
            relative = path.relative_to(_codex_base())
            provider = "codex"
            display_name = f"Codex CLI / {'/'.join(relative.parts)}"
        except ValueError:
            pass

    return {
        "log_path": str(path),
        "dir_name": slug,
        "display_name": display_name,
        "provider": provider,
    }


def resolve_log_slug(slug: str) -> dict[str, Any] | None:
    """
    Resolve a slug back to project metadata. Does not verify the directory exists.
    """
    if not slug:
        return None

    if slug.startswith(CODEX_SLUG_PREFIX):
        remainder = slug[len(CODEX_SLUG_PREFIX) :]
        parts = [part for part in remainder.split("~") if part]
        if not parts:
            return None
        log_path = _codex_base().joinpath(*parts)
        return describe_log_path(str(log_path))

    # Default to Claude project slugs
    log_path = _claude_base() / slug.replace("~", "/")
    return describe_log_path(str(log_path))


def _collect_project_metadata(log_dir: Path) -> dict[str, Any] | None:
    """
    Collect metadata for a log directory shared by Claude and Codex providers.
    """
    if not log_dir.exists() or not log_dir.is_dir():
        return None

    jsonl_files = list(log_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None

    description = describe_log_path(str(log_dir))
    total_size = sum(f.stat().st_size for f in jsonl_files)
    mtimes = [f.stat().st_mtime for f in jsonl_files]

    metadata = {
        **description,
        "file_count": len(jsonl_files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "last_modified": max(mtimes),
        "first_seen": min(mtimes),
    }

    if description["provider"] == "codex":
        try:
            relative = log_dir.relative_to(_codex_base())
            metadata["relative_path"] = "/".join(relative.parts)
        except ValueError:
            metadata["relative_path"] = log_dir.name

    return metadata


def get_all_projects_with_metadata() -> list[dict[str, Any]]:
    """
    Get all known projects (Claude + Codex CLI) with lightweight metadata.

    Returns metadata without reading file contents for performance.
    """
    projects: list[dict[str, Any]] = []

    # Claude projects
    claude_base = _claude_base()
    if claude_base.exists():
        try:
            for log_dir in claude_base.iterdir():
                metadata = _collect_project_metadata(log_dir)
                if metadata:
                    projects.append(metadata)
        except Exception as exc:
            logger.info(f"Error reading Claude project metadata: {exc}")

    # Codex CLI sessions (organized by year/month/day)
    codex_base = _codex_base()
    if codex_base.exists():
        try:
            for year_dir in codex_base.iterdir():
                if not year_dir.is_dir():
                    continue
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir():
                            continue
                        metadata = _collect_project_metadata(day_dir)
                        if metadata:
                            projects.append(metadata)
        except Exception as exc:
            logger.info(f"Error reading Codex session metadata: {exc}")

    return projects
