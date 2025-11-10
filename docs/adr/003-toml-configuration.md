# ADR 003: TOML Configuration in User Home Directory

## Status
Accepted

## Date
2025-11-10

## Context
Originally, the pretty_release_notes CLI tool used a `.env` file in the project directory for configuration. This approach had several limitations:

1. **Inconsistency**: Database files were moved to `~/.pretty-release-notes/` (ADR 002), but configuration remained in the project directory
2. **Format Limitations**: `.env` files use flat key-value pairs with limited structure (no nesting, arrays require comma-separated strings)
3. **Directory Clutter**: Users needed a `.env` file in every directory where they ran the tool
4. **Modern Standards**: TOML is the modern Python standard for configuration (used by Poetry, Ruff, pyproject.toml, etc.)

## Decision
We migrated from `.env` files to TOML configuration with the following changes:

### 1. Configuration File Location
- **New**: `~/.pretty-release-notes/config.toml` (user home directory)
- **Old**: `.env` (project directory)
- **Rationale**: Consistency with database location, user-wide configuration

### 2. Configuration Format
Changed from flat `.env` to structured TOML:

**Old format (`.env`):**
```env
GH_TOKEN=ghp_xxxxx
OPENAI_API_KEY=sk-xxxxx
OPENAI_MODEL=gpt-4.1
DEFAULT_OWNER=frappe
EXCLUDE_PR_TYPES=chore,refactor,ci
```

**New format (`config.toml`):**
```toml
[github]
token = "ghp_xxxxx"
owner = "frappe"

[openai]
api_key = "sk-xxxxx"
model = "gpt-4.1"

[filters]
exclude_change_types = ["chore", "refactor", "ci"]
```

### 3. Implementation
- Created `TomlConfigLoader` class in `pretty_release_notes/core/config_loader.py`
- Uses Python 3.11's built-in `tomllib` module (no additional dependencies)
- Default config path: `~/.pretty-release-notes/config.toml`
- CLI supports `--config-path` flag for custom locations
- Deprecated `EnvConfigLoader` (retained for reference but not used by default)

### 4. Migration Strategy
**No backward compatibility** - breaking change requiring manual migration:
- Users must create `~/.pretty-release-notes/config.toml`
- Provided `config.toml.example` in repository root
- No auto-migration or fallback to `.env`
- **Rationale**: Simpler implementation, clean break from legacy format

## Consequences

### Positive
1. **Consistency**: Configuration and database both in `~/.pretty-release-notes/`
2. **Better Structure**: TOML supports nested sections matching the config hierarchy
3. **Type Safety**: TOML's native types (strings, integers, booleans, arrays) are clearer
4. **User-Friendly**: Single config file shared across all projects
5. **Modern Standard**: Aligns with Python ecosystem conventions
6. **No Dependencies**: Uses built-in `tomllib` (Python 3.11+)

### Negative
1. **Breaking Change**: Users must manually migrate configuration
2. **Migration Required**: No automatic migration or backward compatibility
3. **New Location**: Users must remember config is in home directory, not project directory

### Neutral
1. **CLI Flexibility**: `--config-path` flag allows custom locations if needed
2. **Library Usage**: Unaffected - library users already use programmatic config or `DictConfigLoader`

## Implementation Details

### Files Changed
- `pretty_release_notes/core/config_loader.py` - Added `TomlConfigLoader`
- `pretty_release_notes/main.py` - Changed from `EnvConfigLoader` to `TomlConfigLoader`
- `config.toml.example` - New example configuration file
- `CLAUDE.md` - Updated documentation with new config format
- `tests/test_core.py` - Added comprehensive tests for `TomlConfigLoader`

### Configuration Structure
```toml
# Top-level optional settings (must be before any sections)
prompt_path = ""          # Path to custom prompt file
force_use_commits = false # Force using commits over PRs

[github]          # GitHub authentication
token = ""        # Required
owner = ""        # Optional default owner

[openai]          # OpenAI API settings
api_key = ""      # Required
model = ""        # Optional, default: "gpt-4.1"
max_patch_size    # Optional, default: 10000

[database]        # Cache configuration
type = ""         # "sqlite" or "csv", default: "sqlite"
name = ""         # Filename without extension, default: "stored_lines"
enabled = true    # Enable caching, default: true

[filters]         # Filtering options
exclude_change_types = []   # Array of PR/commit types to exclude
exclude_change_labels = []  # Array of PR labels to exclude
exclude_authors = []        # Array of bot usernames to exclude
```

## Related
- ADR 002: Database files moved to `~/.pretty-release-notes/`
- ADR 001: Multi-mode architecture with strategy pattern for config loaders

## References
- [PEP 518](https://peps.python.org/pep-0518/) - Specifying Minimum Build System Requirements (pyproject.toml)
- [TOML Specification](https://toml.io/)
- [Python tomllib Documentation](https://docs.python.org/3/library/tomllib.html)
