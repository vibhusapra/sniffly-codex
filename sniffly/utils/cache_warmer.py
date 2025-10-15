import asyncio
import logging

from sniffly.config import Config
from sniffly.core.processor import ClaudeLogProcessor
from sniffly.utils.log_finder import get_all_projects_with_metadata

logger = logging.getLogger(__name__)

# Get config instance
_config = Config()
cache_warm_on_startup = _config.get("cache_warm_on_startup")


# Background tasks
async def warm_recent_projects(
    cache_service, memory_cache, current_log_path, exclude_current: bool = False, limit: int = None
):
    """Preload recent projects into memory cache in background"""
    if limit is None:
        limit = cache_warm_on_startup

    try:
        projects = get_all_projects_with_metadata()
        if not projects:
            logger.debug("No projects found to warm")
            return

        # Sort by most recent activity
        projects.sort(key=lambda item: item.get("last_modified", 0), reverse=True)

        warmed = 0
        logger.debug(f"Starting to warm up to {limit} recent projects")

        for project in projects:
            log_path = project["log_path"]

            if exclude_current and log_path == current_log_path:
                continue

            if memory_cache.get(log_path):
                logger.debug(f"{project['dir_name']} already in memory cache")
                continue

            # Respect warm limit
            if warmed >= limit:
                break

            await asyncio.sleep(0.1)

            try:
                processor = ClaudeLogProcessor(log_path)
                messages, stats = processor.process_logs()

                cache_service.save_cached_stats(log_path, stats)
                cache_service.save_cached_messages(log_path, messages)

                if memory_cache.put(log_path, messages, stats, force=True):
                    logger.debug(f"Successfully warmed {project['dir_name']}")
                else:
                    logger.debug(f"Failed to cache {project['dir_name']} (too large)")

                warmed += 1

            except Exception as exc:
                logger.info(f"Error processing {project['dir_name']}: {exc}")

            await asyncio.sleep(0.5)

        logger.debug(f"Completed warming {warmed} projects")

    except Exception as exc:
        logger.info(f"Error in warm_recent_projects: {exc}")
