# ADR 001: Multi-Mode Architecture with Hexagonal Design

## Status
Accepted

## Date
2025-10-21

## Context
The pretty_release_notes project was originally built as a monolithic CLI tool with tightly coupled business logic and UI dependencies. To support multiple usage modes (CLI, Library API, Web Backend), we needed to refactor the architecture while maintaining backward compatibility with the existing CLI interface.

## Decision
We adopted **Hexagonal Architecture** (Ports & Adapters pattern) to isolate core business logic from external concerns, enabling the tool to be used in three modes:
1. **CLI Tool** - Traditional command-line interface (backward compatible)
2. **Python Library** - Programmatic API for integration
3. **Web Backend** - REST API for web frontends

### Key Architectural Decisions

#### 1. Core Abstractions (Ports)
- **ProgressReporter Interface** (`core/interfaces.py`)
  - Event-based progress reporting using `ProgressEvent` dataclass
  - `NullProgressReporter` for silent library usage
  - `CompositeProgressReporter` for multiple simultaneous reporters
  - Enables UI-independent business logic

- **Type-Safe Configuration** (`core/config.py`)
  - Dataclass-based configuration with validation in `__post_init__`
  - Separate configs for: GitHub, OpenAI, Database, Filters
  - Immutable once created, fails fast with clear errors
  - `ReleaseNotesConfig` as main container

- **Configuration Loading Strategies** (`core/config_loader.py`)
  - `EnvConfigLoader` - Load from .env files (CLI backward compatibility)
  - `DictConfigLoader` - Load from dictionaries (library/web usage)
  - Strategy pattern for extensibility

- **Execution Strategies** (`core/execution.py`)
  - `ThreadPoolStrategy` - Managed thread pool (default, max_workers=10)
  - `ThreadingStrategy` - Original direct threading
  - `SequentialStrategy` - For debugging or constrained environments
  - Abstracts parallelism for testability and control

#### 2. Adapters (External Interfaces)
- **CLI Adapter** (`adapters/cli_progress.py`)
  - `CLIProgressReporter` bridges `ProgressReporter` to `CLI` class
  - Routes events to appropriate UI methods
  - Maintains separation between core and CLI concerns

- **Library API** (`api.py`)
  - `ReleaseNotesClient` - High-level client for library users
  - `ReleaseNotesBuilder` - Fluent builder pattern for configuration
  - No CLI dependencies, uses `NullProgressReporter` by default

- **Web API** (`web/app.py`)
  - FastAPI-based REST endpoints
  - `WebProgressReporter` captures events for job status
  - Background task processing with job tracking
  - In-memory job storage (use Redis for production)

#### 3. Business Logic Decoupling
- **ReleaseNotesGenerator** (`generator.py`)
  - Zero UI dependencies (removed direct `ui` imports)
  - Accepts `ReleaseNotesConfig` and optional `ProgressReporter`
  - Uses `ExecutionStrategy` for parallel processing
  - Reports 11 progress events throughout generation workflow

#### 4. Thread-Safe Database Access
- **SQLiteDatabase** (`database.py`)
  - Thread-local connections via `threading.local()`
  - Connection pooling with lock-based transactions
  - Prevents race conditions during concurrent operations

### Design Patterns Applied

1. **Hexagonal Architecture** - Core domain isolated from external concerns
2. **Strategy Pattern** - Configuration loading, execution strategies
3. **Builder Pattern** - Fluent API for library usage
4. **Observer Pattern** - Event-based progress reporting
5. **Factory Pattern** - Database creation (`get_db()`)
6. **Protocol Pattern** - `Change` protocol for polymorphic PR/Commit handling
7. **Adapter Pattern** - CLI, Library, and Web adapters

## Consequences

### Positive
- **Multi-mode support** - CLI, Library, and Web without code duplication
- **backward compatibility** - Existing CLI users unaffected
- **Testability** - Core logic testable without UI dependencies
- **Extensibility** - Easy to add new adapters
- **Type safety** - Configuration validated at creation time
- **Maintainability** - Clear separation of concerns
- **Performance** - Thread pool strategy provides better resource management
- **Concurrency** - Thread-safe database operations

### Negative
- **Increased complexity** - More files and abstractions to understand
- **Learning curve** - New contributors need to understand Hexagonal Architecture
- **Indirection** - More layers between user request and execution

### Neutral
- **Dependencies** - Now managed via `pyproject.toml` instead of requirements.txt
- **Package distribution** - Console script entry point: `pretty-release-notes`
- **Testing** - 77 tests with 75% code coverage

## Implementation Phases

The refactoring was completed in 6 phases:
1. **Core Abstractions** - Interfaces, config, loaders
2. **Business Logic Decoupling** - Remove UI dependencies from generator
3. **Library API** - Builder pattern and client API
4. **Concurrent Execution** - Execution strategies and thread safety
5. **Web Backend** - FastAPI REST API with background jobs
6. **Package Distribution** - pyproject.toml, console scripts, backward compatibility
