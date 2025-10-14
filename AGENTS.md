# Repository Guidelines

## Project Structure & Module Organization
Sniffly’s Python backend lives in `sniffly/` with FastAPI services, CLI entry points, and layered caching utilities under `core/`, `api/`, `utils/`, and `services/`. Frontend assets for the shareable dashboard are versioned in `sniffly/static/` and mirrored for the hosted site in `sniffly-site/`, where `build.py` bundles templates for Cloudflare Pages. Tests mirror this layout in `tests/`, including performance and regression fixtures inside `tests/mock-data/`. Reference material and design notes are curated in `docs/`, while `assets/` contains branding used by the dashboard.

## Build, Test, and Development Commands
- `pip install -e .` installs the package in editable mode; follow with `pip install -r requirements-dev.txt` for tooling.
- `python run_tests.py` runs pytest suites (performance tests are skipped by default).
- `python run_tests.py -c` enables coverage reporting; use `python run_tests.py -p` when you need the performance benchmarks.
- `bash lint.sh` runs Ruff linting/formatting and mypy; fixers run automatically when possible.
- `sniffly init --port 8090` starts the dashboard locally after installation; `scripts/start_local.py` provides an alternate launcher with custom flags.

## Coding Style & Naming Conventions
Python code follows PEP 8 with four-space indentation, Ruff-enforced line length of 120, and module-level typing (mypy is configured to skip tests). Keep modules lowercase with underscores (`log_finder.py`), use `PascalCase` for classes, and `snake_case` for functions and variables. JavaScript modules in `sniffly/static/js/` prefer `camelCase` exports and modular files under the existing naming scheme. Use `ruff format sniffly/ sniffly-site/` before committing; avoid ad-hoc formatting tools to maintain consistent diffs.

## Testing Guidelines
Author tests alongside code in the matching subtree (`sniffly/utils/` → `tests/utils/`). Pytest markers are light, so prefer descriptive function names like `test_cache_evicts_stale_entries`. Performance tests (`tests/test_performance.py`) take longer—only enable them when validating caching or throughput changes. When updating baseline JSON in `tests/baseline_results.json`, document the rationale in the PR and regenerate fixtures through the relevant processor utilities.

## Commit & Pull Request Guidelines
Recent history uses short, imperative commit subjects with optional PR references (`Fix error analysis (#15)`). Keep the first line under 72 characters and reference issues or discussions when applicable. PRs should summarize scope, list validation commands run, and attach screenshots for UI changes from dashboard or share pages. Link to related docs in `docs/` if you update architecture notes, and confirm lint/test status before requesting review.
