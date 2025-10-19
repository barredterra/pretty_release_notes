# Project Overview: Pretty Release Notes

## Purpose

This is a multi-mode Python tool that transforms GitHub's auto-generated release notes into polished, human-readable sentences using OpenAI. It can be used as:
1. **CLI Tool** - Traditional command-line interface
2. **Python Library** - Programmatic API for integration (in development)
3. **Web Backend** - REST API for web frontends (planned)

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
│  │   CLI    │  │  Library │  │   Web    │  (planned)  │
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
main.py                 # CLI entry point
generator.py            # Core business logic (UI-independent)
github_client.py        # GitHub API wrapper
openai_client.py       # OpenAI API wrapper
database.py            # Caching layer (CSV/SQLite)
ui.py                  # Terminal UI (used via adapter)
prompt.txt             # AI prompt template
core/                  # Core abstractions (Hexagonal Architecture)
├── __init__.py        # Package initialization
├── interfaces.py      # ProgressReporter protocol & events
├── config.py          # Type-safe configuration dataclasses
└── config_loader.py   # Configuration loading strategies
adapters/              # Adapters for external interfaces
├── __init__.py        # Package initialization
└── cli_progress.py    # CLI adapter for ProgressReporter
models/                # Data models
├── change.py          # Protocol for PR/Commit interface
├── pull_request.py    # PR data model
├── commit.py          # Commit data model
├── issue.py           # Issue data model
├── repository.py      # Repository data model
├── release_notes.py   # Release notes container
├── release_notes_line.py  # Individual line model
└── _utils.py          # Utility functions
tests/                 # Test suite
├── test_core.py       # Tests for core abstractions
└── ...                # Other test files
```

## Key Components

### Core Abstractions: `core/`

**`core/interfaces.py`** - Progress Reporting Protocol:
- `ProgressEvent`: Dataclass for progress events (type, message, metadata)
- `ProgressReporter`: Abstract interface for progress reporting
- `NullProgressReporter`: No-op implementation for library usage
- `CompositeProgressReporter`: Combine multiple reporters

**`core/config.py`** - Type-Safe Configuration:
- `GitHubConfig`: GitHub token and owner
- `OpenAIConfig`: OpenAI API key, model, max patch size
- `DatabaseConfig`: Database type, name, enabled state
- `FilterConfig`: Exclusion filters for types, labels, authors
- `ReleaseNotesConfig`: Main configuration container
- All configs include validation in `__post_init__`

**`core/config_loader.py`** - Configuration Loading Strategies:
- `ConfigLoader`: Abstract base class
- `DictConfigLoader`: Load from dictionary (for programmatic usage)
- `EnvConfigLoader`: Load from .env file (backward compatibility)

### Adapters: `adapters/`

**`adapters/cli_progress.py`** - CLI Progress Adapter:
- `CLIProgressReporter`: Bridges `ProgressReporter` interface to `CLI` class
- Routes events to appropriate CLI methods (markdown, success, error, release_notes)

### Entry Point: `main.py`
- CLI command using Typer
- Loads configuration using `EnvConfigLoader`
- Creates `CLIProgressReporter` adapter
- Orchestrates: initialize → generate → display → optionally update
- Maintains 100% backward compatibility with original CLI interface

### Core Logic: `generator.py` - `ReleaseNotesGenerator`
- **Constructor**: Accepts `ReleaseNotesConfig` and optional `ProgressReporter`
- **UI-independent**: No direct UI dependencies, uses progress events
- `initialize_repository()`: Fetches repository metadata
- `generate()`: Main workflow for release note generation
  - Retrieves current release
  - Regenerates release notes via GitHub API
  - Parses into structured data
  - Downloads PR information in parallel
  - Falls back to commits if no PRs found
  - Processes lines to generate AI summaries
  - Loads reviewer information in parallel
  - Reports progress via `ProgressEvent` emissions (11 locations)
- `_process_line()`: Core processing with cache checking and OpenAI calls

### GitHub Integration: `github_client.py` - `GitHubClient`
- Authenticated session with Bearer token
- Methods for: repositories, PRs, commits, reviewers, issues, diffs
- Uses REST API and GraphQL API

### AI Integration: `openai_client.py`
- `get_chat_response()`: Wrapped with retry logic
- Exponential backoff: 1-60s, max 6 attempts
- Flex service tier for o3/o4-mini models

### Data Persistence: `database.py`
- Abstract `Database` base class
- `CSVDatabase`: File-based storage
- `SQLiteDatabase`: Indexed queries for performance
- Factory pattern: `get_db()` returns appropriate backend

### UI: `ui.py` - `CLI`
- Uses Rich library for formatted terminal output
- Methods for: markdown display, release notes, confirmations, errors, success

### Models

**`PullRequest` class** (`models/pull_request.py`):
- Extracts backport PR number from title
- Determines conventional commit type
- Constructs AI prompts with issue context and PR patch
- Resolves reviewers (excluding self-reviews and bots)
- Recursively fetches original PR for backports

**`Commit` class** (`models/commit.py`):
- Simpler than PullRequest
- Uses commit diff instead of PR patch
- Truncates large diffs with "[TRUNCATED]" marker

**`ReleaseNotes` class** (`models/release_notes.py`):
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
- `DB_NAME`: Database name (default "stored_lines")
- `DEFAULT_OWNER`: Default repository owner (e.g., "frappe")
- `PROMPT_PATH`: Path to custom prompt file (default "prompt.txt")
- `EXCLUDE_PR_TYPES`: Comma-separated types to exclude (default: "chore,refactor,ci,style,test")
- `EXCLUDE_PR_LABELS`: Comma-separated labels to exclude (default: "skip-release-notes")
- `EXCLUDE_AUTHORS`: Comma-separated bot usernames to exclude
- `FORCE_USE_COMMITS`: Force using commits even when PRs available (default "false")

### Method 2: Programmatic Configuration (Library Usage)

```python
from core.config import ReleaseNotesConfig, GitHubConfig, OpenAIConfig

config = ReleaseNotesConfig(
    github=GitHubConfig(token="ghp_xxxxx", owner="frappe"),
    openai=OpenAIConfig(api_key="sk-xxxxx", model="gpt-4"),
)
```

### Method 3: Dictionary Configuration (Library Usage)

```python
from core.config_loader import DictConfigLoader

loader = DictConfigLoader({
    "github_token": "ghp_xxxxx",
    "openai_api_key": "sk-xxxxx",
    "openai_model": "gpt-4",
    "exclude_types": ["chore", "ci"],
})
config = loader.load()
```

All configurations undergo validation at creation time, raising `ValueError` for invalid values.

## Entry Point Usage

```bash
python main.py [OPTIONS] REPO TAG

# Examples:
python main.py erpnext v15.38.4
python main.py --owner alyf-de banking v0.0.1
```

**CLI Parameters**:
- `repo` (required): Repository name
- `tag` (required): Git tag for release
- `--owner`: Repository owner
- `--database/--no-database`: Enable/disable caching
- `--prompt-path`: Path to custom prompt file
- `--force-use-commits`: Force using commits even when PRs available

## Development Tools

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

### Testing with Pytest

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_pull_request.py
```

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

### 4. Parallel Processing with Threading
Used extensively for performance:
- PR fetching & Line processing (`generator.py`)
- Reviewer loading (`release_notes.py`)
- Reviewer determination (`pull_request.py`)

### 5. Protocol-Based Polymorphism
`Change` protocol allows treating `PullRequest` and `Commit` uniformly:
- Both implement: `get_prompt()`, `set_reviewers()`, `get_author()`, `get_summary_key()`
- Enables consistent processing throughout the codebase

### 6. Factory Pattern
Database creation uses factory pattern:
- `get_db()` returns appropriate concrete class based on `db_type`
- Abstract interface with two implementations

### 7. Intelligent Caching Strategy
- Uses `get_summary_key()` for cache lookups
- Reuses summaries for backport PRs by returning original PR number
- Skips OpenAI API call if cached entry found

### 8. Type-Safe Configuration with Validation
All configuration uses dataclasses with validation:
- `__post_init__` methods validate required fields and value ranges
- Type hints throughout for IDE support and mypy checking
- Fails fast with clear error messages
- Immutable once created (dataclass frozen in future versions)

### 9. Backport Intelligence
Sophisticated backport handling:
- Extracts backport number using regex
- Recursively fetches original PR
- Reuses original PR's closed issues
- Combines reviewers from both PRs
- Credits original author

### 10. Retry Logic with Exponential Backoff
OpenAI API calls use `@retry` decorator:
- Exponential backoff: 1-60 seconds
- Maximum 6 attempts
- Handles transient API failures gracefully

### 11. Graceful Degradation
Multiple fallback mechanisms:
- If release notes generation fails (403), uses existing notes
- If PR patch too large, falls back to commit messages
- If commit diff too large, truncates with marker
- If no PRs found, falls back to commits
- If GitHub update fails (403), continues without error

### 12. Dataclass-Based Models
All models use `@dataclass`:
- Automatic `__init__()`, `__repr__()`, `__eq__()`
- Type hints throughout
- `from_dict()` class methods for API response parsing

### 13. Conventional Commits Support
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
- **API integration** (GitHub + OpenAI) with retry logic
- **Parallel processing** for performance optimization
- **Intelligent caching** for cost optimization
- **Protocol-based design** for flexibility
- **Graceful error handling** with multiple fallback mechanisms

The tool significantly improves release note quality by transforming technical PR titles into user-friendly descriptions while maintaining proper attribution and filtering out non-relevant changes.

## Future Roadmap

### Completed:
- ✅ Phase 1: Core abstractions (interfaces, config, loaders)
- ✅ Phase 2: Business logic decoupling (UI-free generator)

### In Progress:
- 🚧 Phase 3: Library API with builder pattern
- 🚧 Phase 4: Concurrent execution support with thread pools
- 🚧 Phase 5: Web backend with REST API
- 🚧 Phase 6: Package distribution via PyPI

See `thoughts/shared/plans/2025-01-19-multi-mode-architecture.md` for detailed implementation plan.
