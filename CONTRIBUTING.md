# Contributing

Thank you for your interest in contributing to Pretty Release Notes!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/alyf-de/pretty_release_notes
cd pretty_release_notes

# Create a virtual environment
python -m venv env
source env/bin/activate

# Install in editable mode with dev dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

## Running Tests

Run the full test suite:

```bash
pytest
```

Run specific test files:

```bash
pytest tests/test_web_api.py      # Web API tests
pytest tests/test_core.py          # Core configuration tests
pytest tests/test_execution.py     # Concurrent execution tests
```

All tests use mocks to avoid actual API calls, making them fast and reliable. Coverage reports are generated automatically (see `htmlcov/` after a run).

## Pre-commit Hooks

Pre-commit hooks run automatically on every commit. They are configured in `.pre-commit-config.yaml` and include:

- **Ruff** - Linting, import sorting, and formatting (replaces Black, Flake8, isort)
- **Mypy** - Static type checking
- **Standard checks** - Trailing whitespace, merge conflicts, valid JSON/TOML/YAML, debug statements

You can run all hooks manually against the entire codebase:

```bash
pre-commit run --all-files
```

### Ruff

Ruff handles linting and formatting. Configuration lives in `pyproject.toml` under `[tool.ruff]`.

```bash
# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

### Mypy

Mypy performs static type checking. Configuration lives in `pyproject.toml` under `[tool.mypy]`.

```bash
# Check the entire project
mypy .

# Check a specific file
mypy pretty_release_notes/generator.py
```

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/). A `commitlint` hook enforces this on every commit.

The format is:

```
type(scope): description
```

Common types:

| Type       | When to use                               |
|------------|-------------------------------------------|
| `feat`     | A new feature                             |
| `fix`      | A bug fix                                 |
| `docs`     | Documentation changes                     |
| `refactor` | Code restructuring without behavior change|
| `test`     | Adding or updating tests                  |
| `chore`    | Build scripts, CI, dependencies           |
| `perf`     | Performance improvements                  |
| `style`    | Formatting, whitespace (no logic changes) |
| `ci`       | CI/CD configuration changes               |

Examples:

```
feat: add grouping by conventional commit type
fix(generator): handle missing PR patch gracefully
docs: update configuration examples in README
test: add thread-safety tests for SQLite database
chore: bump ruff to v0.8.4
```
