# Project Overview: Pretty Release Notes

## Purpose

This is a multi-mode Python tool that rewrites GitHub's auto-generated release notes into polished, human-readable sentences using an LLM. It can be used as:

1. **CLI Tool** - Traditional command-line workflow
2. **Python Library** - Programmatic API for integration
3. **Web Backend** - FastAPI service for web frontends or automation

It is tuned for ERPNext and the Frappe Framework by default, but can be adapted to other repositories by providing a custom prompt template.

## Core Functionality

- Rewrites GitHub release-note PR lines into clearer, user-facing summaries
- Supports provider-qualified LLM models through `any_llm` (for example `openai:o3`, `openai:gpt-5`, `anthropic:claude-sonnet-4-5`)
- Filters non-user-facing changes by conventional commit type, label, or author
- Detects PRs that were reverted within the same release and removes both the original PR and the revert PR from output
- Reuses cached summaries for direct backports by using the original PR number as the summary key
- Falls back to commit-based generation when PR metadata is unavailable or `force_use_commits` is enabled
- Loads reviewer information and credits authors/reviewers while excluding configured bots
- Supports optional grouping by conventional commit type, with breaking changes rendered first when present
- Stores generated summaries in CSV or SQLite caches
- Supports interactive TOML-based setup and one-time migration from legacy `.env` files
- Can infer the previous tag from the GitHub compare URL in existing release notes when one is not supplied manually

## Technology Stack

- **Language**: Python 3.11+
- **Key Libraries**:
  - `typer` - CLI framework
  - `rich` - terminal output and interactive prompts
  - `requests` - GitHub REST and GraphQL communication
  - `tenacity` - retry logic for LLM calls
  - `python-dotenv` - legacy `.env` loading and migration support
  - `any-llm-sdk[all]` - provider-agnostic LLM access
- **Optional Web Stack**:
  - `fastapi` - REST API
  - `uvicorn` - ASGI server
  - `pydantic` - request/response models
- **External APIs**:
  - GitHub REST API - repositories, PRs, commits, reviews, releases
  - GitHub GraphQL API - issues closed by a PR
  - LLM provider APIs via `any_llm`

## Architecture

The project follows a lightweight **Hexagonal Architecture** / **Ports and Adapters** approach. The core release-note generation logic is UI-agnostic and reusable across CLI, library, and web modes.

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
│       │          Core Domain      │                   │
│  ┌────▼─────────────▼─────────────▼─────┐             │
│  │     ProgressReporter Interface       │             │
│  │   (event-based progress reporting)   │             │
│  └──────────────────────────────────────┘             │
│  ┌──────────────────────────────────────┐             │
│  │  ReleaseNotesConfig / LLMConfig      │             │
│  │  typed configuration with validation │             │
│  └──────────────────────────────────────┘             │
│  ┌──────────────────────────────────────┐             │
│  │      ReleaseNotesGenerator           │             │
│  │   core business logic, UI-free       │             │
│  └──────────────────────────────────────┘             │
└───────────────────────────────────────────────────────┘
```

## Project Structure

```text
pretty_release_notes/                 # Main package
├── __init__.py                       # Public package exports
├── __main__.py                       # `python -m pretty_release_notes`
├── main.py                           # Typer CLI entrypoint
├── setup_command.py                  # Interactive setup / migration helpers
├── api.py                            # Library client and builder
├── generator.py                      # Core release note generation workflow
├── github_client.py                  # GitHub API wrapper
├── openai_client.py                  # LLM adapter (legacy module name)
├── database.py                       # CSV / SQLite cache backends
├── ui.py                             # Rich-based CLI UI
├── prompt.txt                        # Packaged default prompt
├── py.typed                          # PEP 561 marker
├── core/
│   ├── __init__.py
│   ├── config.py                     # Typed configuration models
│   ├── config_loader.py              # TOML, dict, and .env loaders
│   ├── execution.py                  # Parallel execution strategies
│   └── interfaces.py                 # Progress interfaces and events
├── adapters/
│   ├── __init__.py
│   └── cli_progress.py               # CLI ProgressReporter adapter
├── web/
│   ├── __init__.py
│   ├── app.py                        # FastAPI app and background jobs
│   └── server.py                     # Uvicorn runner
└── models/
    ├── __init__.py
    ├── _utils.py                     # Conventional commit helpers
    ├── change.py                     # Change protocol
    ├── commit.py                     # Commit model
    ├── issue.py                      # Linked issue model
    ├── pull_request.py               # Pull request model
    ├── release_notes.py              # Release notes container / serializer
    ├── release_notes_line.py         # Parsed line model
    └── repository.py                 # Repository model

tests/                                # Pytest suite
├── __init__.py
├── pull_request.py                   # PR fixtures
├── test_api.py
├── test_core.py
├── test_database_threading.py
├── test_execution.py
├── test_models_utils.py
├── test_openai_client.py
├── test_pull_request.py
├── test_release_notes.py
├── test_setup_command.py
└── test_web_api.py

docs/adr/                             # Architecture Decision Records
├── 001-multi-mode-architecture.md
├── 002-user-directory-database-storage.md
└── 003-toml-configuration.md

examples/
└── library_usage.py

.github/workflows/                    # CI workflows
├── lint.yml
└── tests.yml

CHANGELOG.md
CLAUDE.md
CONTRIBUTING.md
README.md
config.toml.example                   # Example user config
prompt.txt                            # Root prompt file for development/reference
pyproject.toml                        # Packaging, dependencies, tool config
.pre-commit-config.yaml               # Pre-commit hooks
```

## Key Components

### Core Abstractions: `pretty_release_notes/core/`

**`pretty_release_notes/core/interfaces.py`** - Progress reporting protocol:
- `ProgressEvent`: Dataclass with `type`, `message`, and optional `metadata`
- `ProgressReporter`: Protocol used by the generator and adapters
- `NullProgressReporter`: No-op reporter for silent operation
- `CompositeProgressReporter`: Broadcasts progress to multiple reporters

**`pretty_release_notes/core/config.py`** - Typed configuration:
- `GitHubConfig`: GitHub token and optional default owner
- `LLMConfig`: Provider API key, model name, and max patch size
- `OpenAIConfig`: Backward-compatible alias for `LLMConfig`
- `DatabaseConfig`: Cache backend type, name, and enabled state
- `FilterConfig`: Excluded change types, labels, and authors
- `GroupingConfig`: Grouping toggle, default type headings, `other_heading`, and `breaking_changes_heading`
- `ReleaseNotesConfig`: Main config object; accepts `llm=` or legacy `openai=` inputs and validates required config on creation

**`pretty_release_notes/core/config_loader.py`** - Configuration loaders:
- `ConfigLoader`: Abstract base loader
- `TomlConfigLoader`: Primary CLI loader; reads `~/.pretty-release-notes/config.toml` by default
- `TomlConfigLoader` merges `[llm]` with legacy `[openai]`, with `[llm]` taking precedence
- `DictConfigLoader`: Programmatic loader; supports `llm_*` keys and legacy `openai_*` fallbacks
- `EnvConfigLoader`: Legacy `.env` loader kept for backward compatibility and migration workflows

**`pretty_release_notes/core/execution.py`** - Execution strategies:
- `ExecutionStrategy`: Abstract interface for parallel work
- `ThreadPoolStrategy`: Default strategy used by `ReleaseNotesGenerator`
- `ThreadingStrategy`: Older direct-threading implementation kept for compatibility
- `SequentialStrategy`: Useful for debugging or constrained environments

### Adapters: `pretty_release_notes/adapters/`

**`pretty_release_notes/adapters/cli_progress.py`** - CLI adapter:
- `CLIProgressReporter` translates `ProgressEvent` objects into `CLI` output calls
- Keeps the generator independent from Rich/terminal concerns

### Library API: `pretty_release_notes/api.py`

**`ReleaseNotesClient`** - High-level library interface:
- `generate_release_notes()`: Generate release notes for a repo and tag
- `update_github_release()`: Write generated notes back to GitHub
- Accepts a `ReleaseNotesConfig` plus an optional `ProgressReporter`

**`ReleaseNotesBuilder`** - Fluent builder for library usage:
- `with_github_token()`: Set GitHub authentication
- `with_llm()`: Primary LLM configuration method
- `with_openai()`: Backward-compatible alias for `with_llm()`
- `with_database()`: Configure CSV/SQLite caching
- `with_filters()`: Configure excluded types, labels, and authors
- `with_grouping()`: Enable and customize grouped output headings
- `with_prompt_file()`: Override the prompt template file
- `with_force_commits()`: Force commit-based processing even when PR data exists
- `with_progress_reporter()`: Attach custom progress reporting
- `build()`: Construct a configured `ReleaseNotesClient`

### Web Backend: `pretty_release_notes/web/`

**`pretty_release_notes/web/app.py`** - FastAPI API:
- `POST /generate`: Start a background generation job
- `GET /jobs/{job_id}`: Poll job status, progress, result, or error
- `GET /health`: Health check endpoint
- `GenerateRequest` uses `llm_key` / `llm_model` as primary fields and still accepts `openai_key` / `openai_model`
- Request payload also supports `exclude_types`, `exclude_labels`, and `exclude_authors`
- `WebProgressReporter` stores structured progress events in memory
- Job storage is in-process and in-memory; a persistent store such as Redis would be needed for production

### Entry Points

**`pretty_release_notes/__init__.py`** - Public package API:
- Re-exports `ReleaseNotesBuilder`, `ReleaseNotesClient`, config classes, and progress interfaces
- Exports both `LLMConfig` and the alias `OpenAIConfig`

**`pretty_release_notes/__main__.py`** - Module entrypoint:
- Enables `python -m pretty_release_notes`
- Delegates to `main.app()`

**`pretty_release_notes/main.py`** - CLI:
- Typer app with `generate` and `setup` commands
- Loads TOML config from `~/.pretty-release-notes/config.toml` by default
- Allows CLI overrides for owner, prompt path, database toggle, commit fallback, grouping, and config path
- Uses `CLIProgressReporter` to display progress and results
- Prompts the user before writing updated release notes back to GitHub

**`pretty_release_notes/setup_command.py`** - Interactive setup:
- Creates or updates user config interactively
- Reads existing TOML values to prefill prompts
- Can import legacy values from a project `.env`
- Writes a `[llm]`-based TOML config file
- Contains helper functions for flattening TOML, migrating `.env` values, and rendering TOML output

### Core Logic: `pretty_release_notes/generator.py` - `ReleaseNotesGenerator`

- Constructor accepts `ReleaseNotesConfig`, optional `ProgressReporter`, and optional `ExecutionStrategy`
- Initializes a `GitHubClient` and normalizes commonly used config fields
- `initialize_repository()`: Loads repository metadata before generation/update operations
- `generate()` workflow:
  - Loads the current GitHub release body
  - Infers `previous_tag_name` from the compare URL when needed
  - Tries to regenerate release notes via GitHub
  - Falls back to the existing release body on 403/404 errors
  - Parses lines into `ReleaseNotes`
  - Downloads PR details in parallel
  - Falls back to commit lines when forced or when PR parsing produced no usable changes
  - Processes lines in parallel with cache lookup + LLM summarization
  - Loads reviewers
  - Serializes final markdown with filters, attribution, grouping, and LLM disclosure
- `update_on_github()` updates the release body and gracefully skips 403 errors

### GitHub Integration: `pretty_release_notes/github_client.py` - `GitHubClient`

- Wraps a `requests.Session` with retry-enabled HTTP adapter
- Uses GitHub REST APIs for repositories, releases, PRs, commits, patches, reviews, and diffs
- Uses GitHub GraphQL to load issues closed by a PR
- Returns typed model objects such as `Repository`, `PullRequest`, `Commit`, and `Issue`

### LLM Integration: `pretty_release_notes/openai_client.py` - LLM adapter

Despite the legacy module name, this file is now a generic LLM adapter.

- Uses `any_llm` / `any-llm-sdk[all]` rather than the `openai` SDK directly
- Default model is `openai:o3`
- Supports provider-qualified models such as `openai:gpt-5` or `anthropic:claude-sonnet-4-5`
- Unqualified model names still default to OpenAI for backward compatibility
- Applies OpenAI `service_tier="flex"` for supported `o3`, `o4-mini`, and selected `gpt-5*` models, and `auto` otherwise
- `format_model_name()` produces user-facing model labels for generated notes
- `get_chat_response()` is wrapped in retry logic with random exponential backoff and up to six attempts

### Data Persistence: `pretty_release_notes/database.py`

- `Database`: Base interface for cached sentence storage
- `CSVDatabase`: CSV-backed cache
- `SQLiteDatabase`: Thread-safe SQLite cache
  - Uses thread-local connections/cursors
  - Protects write transactions with a lock
  - Creates the table and index lazily
- `get_db()`: Factory that resolves relative database names into `~/.pretty-release-notes/`
- Absolute database paths are honored as-is

### UI: `pretty_release_notes/ui.py` - `CLI`

- Rich-based terminal UI used by the CLI adapter
- Displays markdown, release notes, errors, success messages, and update confirmations

### Models: `pretty_release_notes/models/`

**`Change` protocol** (`pretty_release_notes/models/change.py`):
- Shared contract for `PullRequest` and `Commit`
- Defines summary, author, reviewer, and prompt-generation behavior

**`PullRequest`** (`pretty_release_notes/models/pull_request.py`):
- Detects direct backports from title suffixes like `(backport #12345)`
- Detects revert PRs from PR body patterns such as `Reverts owner/repo#12345`
- Extracts conventional commit type and breaking-change markers from title
- Builds prompts from the template, linked issues, and either the PR patch or commit messages
- Resolves reviewers, merged-by users, and backport/original PR relationships

**`Commit`** (`pretty_release_notes/models/commit.py`):
- Uses commit message as the source text for conventional commit / breaking-change parsing
- Builds prompts from the template plus commit diff
- Truncates very large diffs with a `[TRUNCATED]` marker

**`ReleaseNotesLine`** (`pretty_release_notes/models/release_notes_line.py`):
- Parses PR URLs out of GitHub-generated note lines
- Preserves "new contributor" lines without sending them to the LLM
- Renders summarized changes as markdown bullets with GitHub links

**`ReleaseNotes`** (`pretty_release_notes/models/release_notes.py`):
- Stores parsed lines
- Loads PR reviewers concurrently
- Filters excluded change types, labels, and reverted PRs
- Supports grouped or flat serialization
- Emits author and reviewer sections
- Appends an AI disclosure section that includes the model name

**Utilities** (`pretty_release_notes/models/_utils.py`):
- `get_conventional_type()`: Extracts conventional commit type
- `is_breaking_change()`: Detects `!`-style breaking changes from commit/PR titles

## Configuration

The tool supports several configuration paths, with TOML as the primary CLI format.

### Method 1: Interactive Setup

Use the setup command to create or update the default config:

```bash
pretty-release-notes setup
```

This command:
- Walks through GitHub, LLM, database, filter, and grouping settings
- Reads existing TOML values when present and uses them as defaults
- Writes the config file to `~/.pretty-release-notes/config.toml`
- Can migrate legacy values from a project `.env`

To seed the prompts from a legacy `.env` file:

```bash
pretty-release-notes setup --migrate-env
```

### Method 2: TOML File (CLI Default)

Primary config location:

```text
~/.pretty-release-notes/config.toml
```

The canonical LLM section is `[llm]`. The legacy `[openai]` section is still accepted for backward compatibility.

```toml
# Optional top-level settings
# prompt_path = "/absolute/path/to/custom_prompt.txt"
# force_use_commits = false

[github]
token = "ghp_xxxxx"
owner = "frappe"

[llm]
api_key = "sk-xxxxx"
model = "openai:o3"
max_patch_size = 10000

[database]
type = "sqlite"
name = "stored_lines"
enabled = true

[filters]
exclude_change_types = ["chore", "refactor", "ci", "style", "test"]
exclude_change_labels = ["skip-release-notes"]
exclude_authors = [
    "mergify[bot]",
    "copilot-pull-request-reviewer[bot]",
    "coderabbitai[bot]",
    "dependabot[bot]",
    "cursor[bot]",
]

[grouping]
group_by_type = false
# type_headings = { feat = "Features", fix = "Bug Fixes" }
# other_heading = "Other Changes"
```

Notes:
- The CLI loads this file through `TomlConfigLoader`
- If `prompt_path` is omitted in TOML, the packaged default prompt is used
- Relative database names are stored under `~/.pretty-release-notes/`
- The example config is in `config.toml.example`

### Method 3: Programmatic Configuration

```python
from pretty_release_notes import GitHubConfig, LLMConfig, ReleaseNotesConfig

config = ReleaseNotesConfig(
    github=GitHubConfig(token="ghp_xxxxx", owner="frappe"),
    llm=LLMConfig(api_key="sk-xxxxx", model="openai:o3"),
)
```

Backward compatibility:
- `OpenAIConfig` is an alias for `LLMConfig`
- `ReleaseNotesConfig(openai=...)` still works, but `llm=` is the primary API

### Method 4: Dictionary Configuration

```python
from pretty_release_notes.core.config_loader import DictConfigLoader

loader = DictConfigLoader(
    {
        "github_token": "ghp_xxxxx",
        "github_owner": "frappe",
        "llm_api_key": "sk-xxxxx",
        "llm_model": "openai:o3",
        "exclude_types": ["chore", "ci"],
    }
)
config = loader.load()
```

Notes:
- `llm_api_key` and `llm_model` are the primary keys
- `openai_api_key` and `openai_model` are still accepted as fallbacks

All configuration paths validate required fields and raise clear errors for missing/invalid values.

## Usage

### CLI Usage

```bash
# Interactive setup
pretty-release-notes setup

# Generate release notes
pretty-release-notes generate [OPTIONS] REPO TAG

# Using python -m
python -m pretty_release_notes setup
python -m pretty_release_notes generate [OPTIONS] REPO TAG

# Examples
pretty-release-notes generate erpnext v15.38.4
pretty-release-notes generate --owner alyf-de banking v0.0.1
pretty-release-notes generate erpnext v15.38.4 --previous-tag v15.38.0
pretty-release-notes generate --config-path /path/to/config.toml erpnext v15.38.4
pretty-release-notes generate --group-by-type erpnext v15.38.4
pretty-release-notes generate --no-database erpnext v15.38.4
```

CLI parameters:
- `repo`: Repository name
- `tag`: Git tag for the release
- `--owner`: Override the configured repository owner
- `--previous-tag`: Specify the previous tag manually
- `--database/--no-database`: Enable or disable caching for this run
- `--prompt-path`: Use a custom prompt file
- `--force-use-commits`: Force commit-based generation
- `--group-by-type`: Enable grouped output
- `--config-path`: Use a non-default TOML config file

### Library Usage

```python
from pathlib import Path

from pretty_release_notes import ReleaseNotesBuilder

client = (
    ReleaseNotesBuilder()
    .with_github_token("ghp_xxxxx")
    .with_llm("sk-xxxxx", model="openai:o3")
    .with_database("sqlite", enabled=True)
    .with_filters(
        exclude_types={"chore", "ci", "refactor"},
        exclude_labels={"skip-release-notes"},
    )
    .with_grouping(
        group_by_type=True,
        type_headings={"feat": "New Features", "fix": "Fixes"},
        other_heading="Other",
    )
    .with_prompt_file(Path("prompt.txt"))
    .build()
)

notes = client.generate_release_notes(
    owner="frappe",
    repo="erpnext",
    tag="v15.38.4",
    previous_tag_name="v15.38.0",
)

client.update_github_release("frappe", "erpnext", "v15.38.4", notes)
```

Notes:
- `with_llm()` is the primary builder API
- `with_openai()` remains available as an alias
- `with_force_commits()` and `with_progress_reporter()` are also available

#### Grouping Release Notes by Type

When grouping is enabled, output is serialized in a consistent order:
- Breaking Changes
- Features
- Bug Fixes
- Performance Improvements
- Documentation
- Code Refactoring
- Tests
- Build System
- CI/CD
- Chores
- Style
- Reverts
- Other Changes
- New Contributors

Only sections with matching content are emitted.

### Web API Usage

Install the web dependencies:

```bash
pip install -e .[web]
```

Start the server:

```bash
python -m uvicorn pretty_release_notes.web.app:app --host 0.0.0.0 --port 8000

# Or use the wrapper module
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
    "previous_tag_name": "v15.38.0",
    "github_token": "ghp_xxx",
    "llm_key": "sk-xxx",
    "llm_model": "openai:o3",
    "exclude_types": ["chore", "ci", "refactor"],
    "exclude_labels": ["skip-release-notes"],
    "exclude_authors": ["dependabot[bot]"]
  }'
```

Notes:
- `openai_key` and `openai_model` are still accepted as request aliases
- The API serves interactive docs at `http://localhost:8000/docs`

Check job status:

```bash
curl http://localhost:8000/jobs/{job_id}
```

Health check:

```bash
curl http://localhost:8000/health
```

## Development Tools

### Package Installation

```bash
# Install core package
pip install -e .

# Install web extras
pip install -e .[web]

# Install dev tools
pip install -e .[dev]
```

### Pre-commit Hooks

Pre-commit is configured in `.pre-commit-config.yaml`.

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

Configured hooks include:
- Standard repository checks (trailing whitespace, merge conflicts, JSON/TOML/YAML, debug statements)
- Ruff import sorting
- Ruff linting
- Ruff formatting
- Mypy
- Commitlint on `commit-msg` using the conventional commits preset

### Ruff

```bash
# Format code
ruff format .

# Check formatting
ruff format --check .

# Lint code
ruff check .

# Auto-fix lint issues
ruff check --fix .
```

Ruff is used for formatting, import sorting, and linting.

### Mypy

```bash
# Check the whole project
mypy .

# Check a specific file
mypy pretty_release_notes/generator.py
```

### Pytest

```bash
# Run the full test suite
pytest

# Run with coverage
pytest --cov=pretty_release_notes --cov-report=html --cov-report=term-missing

# Run a specific test file
pytest tests/test_web_api.py
```

The test suite covers configuration loaders, core abstractions, builder/API behavior, setup migration, release note serialization, revert/backport logic, web endpoints, threading, and the LLM adapter.

## Notable Design Patterns

### 1. Hexagonal Architecture
Core generation logic is kept separate from CLI, library, and web adapters.

### 2. Event-Based Progress Reporting
`ProgressReporter` implementations receive `ProgressEvent` objects from the generator, allowing different frontends to display progress differently.

### 3. Strategy Pattern for Configuration Loading
`TomlConfigLoader`, `DictConfigLoader`, and `EnvConfigLoader` all produce the same `ReleaseNotesConfig` shape.

### 4. Strategy Pattern for Parallel Execution
`ReleaseNotesGenerator` delegates parallel work to an `ExecutionStrategy`, making threading behavior swappable and testable.

### 5. Protocol-Based Change Abstraction
The `Change` protocol lets `PullRequest` and `Commit` participate in the same summarization pipeline.

### 6. Factory Pattern for Cache Backends
`get_db()` returns either a CSV or SQLite backend based on configuration.

### 7. Intelligent Caching and Backport Reuse
Summaries are cached by `get_summary_key()`, allowing direct backports to reuse the original PR summary.

### 8. Provider-Agnostic LLM Integration
The code uses `any_llm` with provider-qualified model names while preserving OpenAI-oriented backward compatibility in config and request fields.

### 9. Conventional Commit and Breaking-Change Grouping
Commit/PR titles are parsed for conventional commit types and `!` breaking-change markers, which drive filtering and grouped output.

### 10. Automatic Revert Detection and Filtering
Revert PRs are detected from PR body text. When both the original PR and its revert are in the same release, both are excluded from the final notes.

### 11. Graceful Degradation
The generator can fall back from GitHub regeneration to existing notes, from PR patches to commit messages, and from PR-based notes to raw commits when necessary.

### 12. Thread-Safe SQLite Access
SQLite writes are synchronized with a lock while each thread gets its own connection/cursor pair.

### 13. Retry Logic with Exponential Backoff
LLM calls are retried with randomized exponential backoff up to six attempts.

### 14. Dataclass-Driven Models and Config
Most configuration and model objects are dataclasses, which keeps construction, validation, and typing straightforward.

## Workflow

1. Initialize repository metadata from GitHub.
2. Load the current GitHub release.
3. Infer the previous tag from the compare URL when it is not provided explicitly.
4. Ask GitHub to regenerate release notes for the requested range.
5. Fall back to the existing release body if regeneration is unavailable.
6. Parse the release notes into structured lines.
7. Download PR details in parallel for lines that reference PR URLs.
8. Fall back to commit-based lines when forced or when GitHub-generated PR parsing did not produce usable changes.
9. Build prompts, consult the cache, and summarize remaining changes with the configured LLM.
10. Load reviewers.
11. Serialize the final markdown with filters, attribution, grouping, and AI disclosure.
12. Display the result and optionally write it back to GitHub.

## Summary

This codebase combines:
- A reusable release-note generation core
- Multiple delivery modes (CLI, library, web)
- Typed config with backward-compatible migration paths
- Provider-agnostic LLM integration
- Cache-backed summarization
- Parallel GitHub data collection
- Filtering, grouping, backport reuse, and revert suppression

It is structured for extension: new loaders, adapters, execution strategies, or storage backends can be added without reworking the core generator.

## Architecture Decisions

Key architecture decisions are documented in ADRs:

- **ADR 001**: Multi-Mode Architecture with Hexagonal Design
  - Documents the move from a CLI-only workflow to reusable core logic with adapters
- **ADR 002**: User Directory Database Storage
  - Documents storing cache files in `~/.pretty-release-notes/` instead of the project directory
- **ADR 003**: TOML Configuration in User Home Directory
  - Documents the move from project-local `.env` files to `~/.pretty-release-notes/config.toml`
