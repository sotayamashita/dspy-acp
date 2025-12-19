# Repository Guidelines

## Project Structure & Module Organization
- `src/dspy_acp/`: Core package implementation (e.g., `adapter.py`).
- `examples/`: Usage samples (see `examples/basic_usage.py`).
- `README.md`: User-facing overview and setup.
- `spec.md`: Protocol and architecture details.
- Tests are not yet present; add them under `tests/` when introduced.

## Build, Test, and Development Commands
- `uv sync`: Install project and dev dependencies from `pyproject.toml`/`uv.lock`.
- `uv run python examples/basic_usage.py`: Run the sample adapter flow locally.
- `uv run ruff check .`: Lint the codebase.
- `uv run ruff format .`: Auto-format code (Ruff formatter).
- `uv run pre-commit install`: Enable pre-commit hooks locally.
- `uv run pre-commit run --all-files`: Run the full pre-commit suite.
- `uv run pytest`: Run tests (once `tests/` exists).

## Coding Style & Naming Conventions
- Python 3.10+ with type hints; keep signatures explicit.
- Indentation: 4 spaces; follow PEP 8.
- Naming: `snake_case` for functions/vars, `CapWords` for classes, `_leading_underscore` for internal helpers.
- Prefer short, focused docstrings for public classes/methods.

## Testing Guidelines
- Framework: `pytest` (dev dependency).
- Naming: `tests/test_*.py` with descriptive test names (e.g., `test_session_init.py`).
- Aim to cover adapter lifecycle, session/auth flows, and error cases.

## Commit & Pull Request Guidelines
- No established commit convention yet; use concise, imperative subjects (e.g., “Add ACP session reset”).
- PRs should include a short summary, testing status, and any user-facing changes.
- If behavior changes, update `README.md` and `spec.md` as needed.

## Configuration & Security Notes
- Authentication can rely on env vars (`OPENAI_API_KEY`, `CODEX_API_KEY`) or browser login.
- Default backend uses `npx @zed-industries/codex-acp`; ensure Node.js is available.
- Do not commit credentials or auth tokens.
