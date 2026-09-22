# fswatch-and-convert — Agent Instructions

## Project Overview
Python CLI that watches a directory for new video files and converts them to still images via ffmpeg. 
Also, it is planned that once a still image is generated, this app lets Draw Things app continue to work.
Built with typer, watchdog, loguru.

## Environment
- Python >= 3.13, managed with `uv`
- Run script: `./1` (or `uv run python -m main <work-dir> <watch-dir> <pattern> <ext>`)
- Dev deps: black, isort, pytest, pytest-mock

## Code Conventions
- CLI entrypoint: `main.py` (typer `@app.command`)
- Logging via `loguru` (`logger.info/exception/warning`)
- Type hints use `str`, `Path`, `Tuple[str, str]`, `list[str]`
- Tests: `unittest.TestCase` + `unittest.mock.patch`/`MagicMock`; no pytest-style fixtures outside `conftest.py`
- Watchdog handler: `CustomFileSystemEventHandler`, filters via regex on `event.src_path`

## Testing
- `pytest` runs tests in `tests/`
- `tests/conftest.py` adds project root to `sys.path`
- Run: `uv run pytest`
- Do not add tests where no tests exist; follow the adjacent unittest + patch style

## File Layout
- `main.py` — all application logic (CLI, converter, event handler)
- `tests/test_main.py` — tests for `VideoConverter`, `GlobalConfig`, `CustomFileSystemEventHandler`
- `1` — bash runner script
