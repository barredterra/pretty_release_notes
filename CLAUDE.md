# Project Overview: Pretty Release Notes

## Purpose

This is a multi-mode Python tool that transforms GitHub's auto-generated release notes into polished, human-readable sentences using OpenAI. It can be used as:
1. **CLI Tool** - Traditional command-line interface
2. **Python Library** - Programmatic API for integration
3. **Web Backend** - REST API for web frontends

It's designed for ERPNext and Frappe Framework projects but can be adapted for other repositories.

## Core Functionality

- Converts PR titles into clear, user-friendly sentences using AI
- Filters out non-user-facing commits (chore, ci, refactor)
- Intelligently handles backport PRs by reusing summaries
- Credits human authors and reviewers (excludes bots)
- Caches generated summaries to avoid redundant API calls

## Technology Stack

- **Language**: Python 3.11+
- **Key Libraries**:
  - `typer` - CLI framework with type hints
  - `openai` - AI integration for summarization
  - `requests` - GitHub API interactions
  - `tenacity` - Retry logic with exponential backoff
  - `rich` - Terminal UI formatting
  - `fastapi` - Web API framework (optional)
  - `uvicorn` - ASGI server (optional)
- **APIs**:
  - GitHub REST API - Repository, PR, commit, release data
  - GitHub GraphQL API - Linked issues
  - OpenAI Chat Completions - AI-powered summarization

## Architecture

The project follows **Hexagonal Architecture** (Ports & Adapters pattern) to support multiple usage modes while maintaining clean separation of concerns.

### Architecture Layers

```
┌───────────────────────────────────────────────────────┐
│                   Adapters (External)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   CLI    │  │  Library │  │   Web    │             │
│  │ Adapter  │  │   API    │  │   API    │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼───────────────────┘
        │             │             │
┌───────┼─────────────┼─────────────┼───────────────────┐
│       │      Core Domain (Ports)  │                   │
│  ┌────▼─────────────▼─────────────▼─────┐             │
│  │     ProgressReporter Interface       │             │
│  │   (Event-based progress reporting)   │             │
│  └──────────────────────────────────────┘             │
│  ┌──────────────────────────────────────┐             │
│  │    ReleaseNotesConfig (typed)        │             │
│  │  Configuration with validation       │             │
│  └──────────────────────────────────────┘             │
│  ┌──────────────────────────────────────┐             │
│  │      ReleaseNotesGenerator           │             │
│  │   (Core business logic - UI free)    │             │
│  └──────────────────────────────────────┘             │
└───────────────────────────────────────────────────────┘
```

## Project Structure

```
pretty_release_notes/   # Main package directory
├── __init__.py         # Package exports (public API)
├── __main__.py         # CLI entry via python -m
├── main.py             # CLI implementation
├── api.py              # Library API (ReleaseNotesClient, ReleaseNotesBuilder)
├── generator.py        # Core business logic (UI-independent)
├── github_client.py    # GitHub API wrapper
├── openai_client.py    # OpenAI API wrapper
├── database.py         # Caching layer (CSV/SQLite with thread-safety)
├── ui.py               # Terminal UI (used via adapter)
├── py.typed            # PEP 561 type marker
├── core/               # Core abstractions (Hexagonal Architecture)
│   ├── __init__.py     # Package initialization
│   ├── interfaces.py   # ProgressReporter protocol & events
│   ├── config.py       # Type-safe configuration dataclasses
│   ├── config_loader.py # Configuration loading strategies
│   └── execution.py    # Execution strategies (ThreadPool, Sequential)
├── adapters/           # Adapters for external interfaces
│   ├── __init__.py     # Package initialization
│   └── cli_progress.py # CLI adapter for ProgressReporter
├── web/                # Web API backend
│   ├── __init__.py     # Package initialization
│   ├── app.py          # FastAPI application with endpoints
│   └── server.py       # Uvicorn server runner
└── models/             # Data models
    ├── __init__.py     # Model re-exports
    ├── change.py       # Protocol for PR/Commit interface
    ├── pull_request.py # PR data model
    ├── commit.py       # Commit data model
    ├── issue.py        # Issue data model
    ├── repository.py   # Repository data model
    ├── release_notes.py # Release notes container
    ├── release_notes_line.py # Individual line model
    └── _utils.py       # Utility functions
tests/                  # Test suite (77 tests, 58% coverage)
├── __init__.py         # Test package
├── test_core.py        # Tests for core abstractions
├── test_api.py         # Tests for library API
├── test_execution.py   # Tests for execution strategies
├── test_database_threading.py # Thread-safety tests
├── test_web_api.py     # Tests for web endpoints
└── pull_request.py     # Pull request test fixtures
examples/               # Usage examples
└── library_usage.py    # Library API examples
docs/adr/               # Architecture Decision Records
└── 001-multi-mode-architecture.md # Hexagonal architecture decisions
prompt.txt              # AI prompt template
pyproject.toml          # Package configuration and dependencies
.pre-commit-config.yaml # Pre-commit hooks (ruff, mypy)
.env                    # Environment configuration (not in repo)
.env.example            # Example environment configuration
```

## Key Components

### Core Abstractions: `pretty_release_notes/core/`

**`pretty_release_notes/core/interfaces.py`** - Progress Reporting Protocol:
- `ProgressEvent`: Dataclass for progress events (type, message, metadata)
- `ProgressReporter`: Abstract interface for progress reporting
- `NullProgressReporter`: No-op implementation for library usage
- `CompositeProgressReporter`: Combine multiple reporters

**`pretty_release_notes/core/config.py`** - Type-Safe Configuration:
- `GitHubConfig`: GitHub token and owner
- `OpenAIConfig`: OpenAI API key, model, max patch size
- `DatabaseConfig`: Database type, name, enabled state
- `FilterConfig`: Exclusion filters for types, labels, authors
- `ReleaseNotesConfig`: Main configuration container
- All configs include validation in `__post_init__`

**`pretty_release_notes/core/config_loader.py`** - Configuration Loading Strategies:
- `ConfigLoader`: Abstract base class
- `DictConfigLoader`: Load from dictionary (for programmatic usage)
- `EnvConfigLoader`: Load from .env file (backward compatibility)

**`pretty_release_notes/core/execution.py`** - Execution Strategies:
- `ExecutionStrategy`: Abstract interface for parallel execution
- `ThreadPoolStrategy`: Managed thread pool (default, max_workers=10)
- `ThreadingStrategy`: Original direct threading implementation
- `SequentialStrategy`: For debugging or constrained environments

### Adapters: `pretty_release_notes/adapters/`

**`pretty_release_notes/adapters/cli_progress.py`** - CLI Progress Adapter:
- `CLIProgressReporter`: Bridges `ProgressReporter` interface to `CLI` class
- Routes events to appropriate CLI methods (markdown, success, error, release_notes)

### Library API: `pretty_release_notes/api.py`

**`ReleaseNotesClient`** - High-level client for library usage:
- `generate_release_notes()`: Generate notes for a repository and tag
- `update_github_release()`: Update release notes on GitHub
- Accepts `ReleaseNotesConfig` and optional `ProgressReporter`

**`ReleaseNotesBuilder`** - Fluent builder pattern:
- `with_github_token()`: Configure GitHub authentication
- `with_openai()`: Configure OpenAI API
- `with_database()`: Configure caching
- `with_filters()`: Configure PR/commit filtering
- `with_progress_reporter()`: Add custom progress reporting
- `build()`: Construct configured client

### Web Backend: `pretty_release_notes/web/`

**`pretty_release_notes/web/app.py`** - FastAPI REST API:
- `POST /generate`: Create release notes generation job (background task)
- `GET /jobs/{job_id}`: Get job status and result
- `GET /health`: Health check endpoint
- `WebProgressReporter`: Captures progress events for job tracking
- In-memory job storage (use Redis for production)

### Entry Points

**`pretty_release_notes/__init__.py`** - Package API:
- Public API exports: `ReleaseNotesBuilder`, `ReleaseNotesClient`, config classes, interfaces
- Enables: `from pretty_release_notes import ReleaseNotesBuilder`

**`pretty_release_notes/__main__.py`** - Module Entry:
- Enables: `python -m pretty_release_notes`
- Delegates to `main.app()`

**`pretty_release_notes/main.py`** - CLI Implementation:
- CLI command using Typer
- Loads configuration using `EnvConfigLoader`
- Creates `CLIProgressReporter` adapter
- Orchestrates: initialize → generate → display → optionally update
- Maintains backward compatibility with original CLI interface
- Console script entry point: `pretty-release-notes = "pretty_release_notes.main:app"`

### Core Logic: `pretty_release_notes/generator.py` - `ReleaseNotesGenerator`
- **Constructor**: Accepts `ReleaseNotesConfig`, optional `ProgressReporter`, and optional `ExecutionStrategy`
- **UI-independent**: No direct UI dependencies, uses progress events
- `initialize_repository()`: Fetches repository metadata
- `generate()`: Main workflow for release note generation
  - Retrieves current release
  - Regenerates release notes via GitHub API
  - Parses into structured data
  - Downloads PR information in parallel (using execution strategy)
  - Falls back to commits if no PRs found
  - Processes lines to generate AI summaries in parallel
  - Loads reviewer information in parallel
  - Reports progress via `ProgressEvent` emissions (11 locations)
- `_process_line()`: Core processing with cache checking and OpenAI calls

### GitHub Integration: `pretty_release_notes/github_client.py` - `GitHubClient`
- Authenticated session with Bearer token
- Methods for: repositories, PRs, commits, reviewers, issues, diffs
- Uses REST API and GraphQL API

### AI Integration: `pretty_release_notes/openai_client.py`
- `get_chat_response()`: Wrapped with retry logic
- Exponential backoff: 1-60s, max 6 attempts
- Flex service tier for o3/o4-mini models

### Data Persistence: `pretty_release_notes/database.py`
- Abstract `Database` base class
- `CSVDatabase`: File-based storage
- `SQLiteDatabase`: Thread-safe with thread-local connections
  - Uses `threading.local()` for connection pooling
  - Lock-based transactions for safe concurrent access
- Factory pattern: `get_db()` returns appropriate backend
- **Storage location**: Relative paths (default) stored in `~/.pretty-release-notes/`, absolute paths stored at exact location

### UI: `pretty_release_notes/ui.py` - `CLI`
- Uses Rich library for formatted terminal output
- Methods for: markdown display, release notes, confirmations, errors, success

### Models: `pretty_release_notes/models/`

**`PullRequest` class** (`pretty_release_notes/models/pull_request.py`):
- Extracts backport PR number from title
- Determines conventional commit type
- Constructs AI prompts with issue context and PR patch
- Resolves reviewers (excluding self-reviews and bots)
- Recursively fetches original PR for backports

**`Commit` class** (`pretty_release_notes/models/commit.py`):
- Simpler than PullRequest
- Uses commit diff instead of PR patch
- Truncates large diffs with "[TRUNCATED]" marker

**`ReleaseNotes` class** (`pretty_release_notes/models/release_notes.py`):
- Container for all release note lines
- Parallel reviewer fetching
- Serializes to markdown with exclusion filters
- Generates author and reviewer lists
- Adds AI disclosure

## Configuration

The tool supports multiple configuration methods:

### Method 1: .env File (CLI Default)

Primary config file for CLI usage: `.env`

- `GH_TOKEN`: GitHub API token (required)
- `OPENAI_API_KEY`: OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default "gpt-4.1")
- `MAX_PATCH_SIZE`: Max patch size before fallback (default 10000)
- `DB_TYPE`: Database backend - "csv" or "sqlite" (default "sqlite")
- `DB_NAME`: Database filename without extension (default "stored_lines"). If relative, stores in `~/.pretty-release-notes/`. If absolute path, stores at that exact location.
- `DEFAULT_OWNER`: Default repository owner (e.g., "frappe")
- `PROMPT_PATH`: Path to custom prompt file (default "prompt.txt")
- `EXCLUDE_PR_TYPES`: Comma-separated types to exclude (default: "chore,refactor,ci,style,test")
- `EXCLUDE_PR_LABELS`: Comma-separated labels to exclude (default: "skip-release-notes")
- `EXCLUDE_AUTHORS`: Comma-separated bot usernames to exclude
- `FORCE_USE_COMMITS`: Force using commits even when PRs available (default "false")

### Method 2: Programmatic Configuration (Library Usage)

```python
from pretty_release_notes import ReleaseNotesConfig, GitHubConfig, OpenAIConfig

config = ReleaseNotesConfig(
    github=GitHubConfig(token="ghp_xxxxx", owner="frappe"),
    openai=OpenAIConfig(api_key="sk-xxxxx", model="gpt-4"),
)
```

### Method 3: Dictionary Configuration (Library Usage)

```python
from pretty_release_notes.core.config_loader import DictConfigLoader

loader = DictConfigLoader({
    "github_token": "ghp_xxxxx",
    "openai_api_key": "sk-xxxxx",
    "openai_model": "gpt-4",
    "exclude_types": ["chore", "ci"],
})
config = loader.load()
```

All configurations undergo validation at creation time, raising `ValueError` for invalid values.

## Usage

### CLI Usage

```bash
# Using installed console script (recommended)
pretty-release-notes [OPTIONS] REPO TAG

# Using python -m (alternative)
python -m pretty_release_notes [OPTIONS] REPO TAG

# Examples:
pretty-release-notes erpnext v15.38.4
pretty-release-notes --owner alyf-de banking v0.0.1
python -m pretty_release_notes --owner frappe erpnext v15.38.4
```

**CLI Parameters**:
- `repo` (required): Repository name
- `tag` (required): Git tag for release
- `--owner`: Repository owner
- `--database/--no-database`: Enable/disable caching
- `--prompt-path`: Path to custom prompt file
- `--force-use-commits`: Force using commits even when PRs available

### Library Usage

```python
from pretty_release_notes import ReleaseNotesBuilder

# Build client with fluent API
client = (
    ReleaseNotesBuilder()
    .with_github_token("ghp_xxxxx")
    .with_openai("sk-xxxxx", model="gpt-4")
    .with_database("sqlite", enabled=True)
    .with_filters(
        exclude_types={"chore", "ci", "refactor"},
        exclude_labels={"skip-release-notes"},
    )
    .build()
)

# Generate release notes
notes = client.generate_release_notes("frappe", "erpnext", "v15.38.4")
print(notes)

# Optionally update on GitHub
client.update_github_release("frappe", "erpnext", "v15.38.4", notes)
```

### Web API Usage

Start the server:
```bash
# Install web dependencies
pip install -e .[web]

# Run server
python -m uvicorn pretty_release_notes.web.app:app --host 0.0.0.0 --port 8000

# Or using the provided server script
python -m pretty_release_notes.web.server
```

Create a generation job:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "frappe",
    "repo": "erpnext",
    "tag": "v15.38.4",
    "github_token": "ghp_xxx",
    "openai_key": "sk-xxx"
  }'
```

Check job status:
```bash
curl http://localhost:8000/jobs/{job_id}
```

## Development Tools

### Package Installation

```bash
# Install in editable mode
pip install -e .

# Install with web dependencies
pip install -e .[web]

# Install with dev dependencies
pip install -e .[dev]
```

### Pre-commit Hooks

Pre-commit hooks automatically run quality checks on commit:

```bash
# Install hooks (run once)
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

Hooks include:
- Ruff linter and formatter
- Mypy type checker
- Standard checks (trailing whitespace, merge conflicts, etc.)
- Commitlint for conventional commit messages

### Code Quality with Ruff

Ruff is used for both linting and formatting (replaces Black, Flake8, isort, and more):

```bash
# Format code
ruff format .

# Check formatting without changes
ruff format --check .

# Lint code
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Run both linting and formatting
ruff check . && ruff format .
```

**Configuration**: See `[tool.ruff]` section in `pyproject.toml`

### Type Checking with Mypy

```bash
# Check types
mypy .

# Check specific file
mypy generator.py
```

**Configuration**: See `[tool.mypy]` section in `pyproject.toml`

### Testing with Pytest

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_web_api.py
```

**Test Suite**: 77 tests with 75% code coverage
**Configuration**: See `[tool.pytest.ini_options]` section in `pyproject.toml`

## Notable Design Patterns

### 1. Hexagonal Architecture (Ports & Adapters)
Core business logic is completely isolated from external concerns:
- **Ports**: `ProgressReporter` interface, `ReleaseNotesConfig` dataclasses
- **Adapters**: `CLIProgressReporter`, `EnvConfigLoader`, `DictConfigLoader`
- **Core Domain**: `ReleaseNotesGenerator` has zero UI dependencies
- Enables multiple usage modes (CLI, Library, Web) without touching core logic

### 2. Event-Based Progress Reporting
Observer pattern implementation for progress updates:
- `ProgressEvent` carries type, message, and optional metadata
- `ProgressReporter` interface allows multiple implementations
- `NullProgressReporter` for silent operation (library usage)
- `CompositeProgressReporter` for multiple simultaneous reporters
- 11 progress events emitted during generation workflow

### 3. Strategy Pattern for Configuration
Multiple strategies for loading configuration:
- `EnvConfigLoader` for .env files (CLI backward compatibility)
- `DictConfigLoader` for programmatic usage (library mode)
- All produce the same `ReleaseNotesConfig` output
- Easy to add new loaders (YAML, JSON, etc.)

### 4. Strategy Pattern for Execution
Abstracts parallel execution for flexibility:
- `ThreadPoolStrategy` - Managed thread pool (default, 10 workers)
- `ThreadingStrategy` - Original direct threading
- `SequentialStrategy` - For debugging or testing
- Enables testing without actual parallelism
- Better resource management than direct threading

### 5. Parallel Processing with Threading
Used extensively for performance:
- PR fetching & Line processing (`generator.py`)
- Reviewer loading (`release_notes.py`)
- Reviewer determination (`pull_request.py`)
- Uses execution strategy for controlled parallelism

### 6. Protocol-Based Polymorphism
`Change` protocol allows treating `PullRequest` and `Commit` uniformly:
- Both implement: `get_prompt()`, `set_reviewers()`, `get_author()`, `get_summary_key()`
- Enables consistent processing throughout the codebase

### 7. Factory Pattern
Database creation uses factory pattern:
- `get_db()` returns appropriate concrete class based on `db_type`
- Abstract interface with two implementations

### 8. Intelligent Caching Strategy
- Uses `get_summary_key()` for cache lookups
- Reuses summaries for backport PRs by returning original PR number
- Skips OpenAI API call if cached entry found

### 9. Type-Safe Configuration with Validation
All configuration uses dataclasses with validation:
- `__post_init__` methods validate required fields and value ranges
- Type hints throughout for IDE support and mypy checking
- Fails fast with clear error messages
- Immutable once created (dataclass frozen in future versions)

### 10. Backport Intelligence
Sophisticated backport handling:
- Extracts backport number using regex
- Recursively fetches original PR
- Reuses original PR's closed issues
- Combines reviewers from both PRs
- Credits original author

### 11. Retry Logic with Exponential Backoff
OpenAI API calls use `@retry` decorator:
- Exponential backoff: 1-60 seconds
- Maximum 6 attempts
- Handles transient API failures gracefully

### 12. Graceful Degradation
Multiple fallback mechanisms:
- If release notes generation fails (403), uses existing notes
- If PR patch too large, falls back to commit messages
- If commit diff too large, truncates with marker
- If no PRs found, falls back to commits
- If GitHub update fails (403), continues without error

### 13. Dataclass-Based Models
All models use `@dataclass`:
- Automatic `__init__()`, `__repr__()`, `__eq__()`
- Type hints throughout
- `from_dict()` class methods for API response parsing

### 14. Conventional Commits Support
Extracts commit types using regex:
- Matches format: `type(scope): message`
- Used for filtering non-user-facing changes

## Workflow

1. **Initialize**: Fetch repository metadata from GitHub
2. **Generate Release Notes**: Use GitHub's auto-generator
3. **Parse**: Convert to structured data model
4. **Fetch Details**: Download PR/commit information in parallel
5. **Process**: For each line:
   - Check cache for existing summary
   - If not cached, construct AI prompt with context
   - Call OpenAI API to generate summary
   - Store in cache
6. **Load Reviewers**: Fetch reviewer information in parallel
7. **Serialize**: Format as markdown with exclusions and credits
8. **Display**: Show in terminal with rich formatting
9. **Update** (optional): Write back to GitHub release

## Summary

This codebase demonstrates a well-structured approach to:
- **Hexagonal Architecture** for multi-mode support (CLI, Library, Web)
- **Clean separation of concerns** with zero UI dependencies in core logic
- **Event-based progress reporting** for flexible output handling
- **Type-safe configuration** with validation and multiple loading strategies
- **Execution strategies** for controlled parallelism and testability
- **Thread-safe database** operations for concurrent access
- **API integration** (GitHub + OpenAI) with retry logic
- **Parallel processing** for performance optimization
- **Intelligent caching** for cost optimization
- **Protocol-based design** for flexibility
- **Graceful error handling** with multiple fallback mechanisms

The tool significantly improves release note quality by transforming technical PR titles into user-friendly descriptions while maintaining proper attribution and filtering out non-relevant changes.

## Architecture Decisions

Key architectural decisions are documented in Architecture Decision Records (ADRs):
- **ADR 001**: Multi-Mode Architecture with Hexagonal Design (`docs/adr/001-multi-mode-architecture.md`)
  - Documents the transition from monolithic CLI to multi-mode architecture
  - Explains all design patterns and their rationale
  - Covers consequences and trade-offs
