# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **TOML Configuration**: New TOML-based configuration format stored in `~/.pretty-release-notes/config.toml`. Provides structured, human-readable configuration with sections for GitHub, OpenAI, database, and filters.
- **Interactive Setup Command**: New `pretty-release-notes setup` command with interactive prompts for creating and updating configuration files. Shows existing values as defaults and validates all inputs.
- **Configuration Migration**: Setup command can migrate from legacy `.env` files using the `--migrate-env` flag.

### Changed
- **Database Storage Location**: Database files are now stored in `~/.pretty-release-notes/` by default instead of the project directory. This provides better separation between user data and application code, follows platform conventions, and avoids permission issues.
- **Configuration Format**: TOML is now the default configuration format. The `.env` format is still supported via `EnvConfigLoader` but is considered legacy.

### Fixed
- **Empty String Defaults**: Setup command now correctly handles empty strings in existing config files, falling back to proper defaults instead of keeping empty values.

### Migration Guide

#### Migrating to TOML Configuration

If you're currently using a `.env` file for configuration, you have two options:

**Option 1: Automated Migration (Recommended)**
```bash
# Run the interactive setup with migration flag
pretty-release-notes setup --migrate-env
```

This will:
- Read your existing `.env` file
- Show all values as defaults in interactive prompts
- Create the new TOML config at `~/.pretty-release-notes/config.toml`
- Optionally delete the old `.env` file

**Option 2: Manual Migration**
1. Copy the example config:
   ```bash
   mkdir -p ~/.pretty-release-notes
   cp config.toml.example ~/.pretty-release-notes/config.toml
   ```

2. Edit the file with your credentials:
   ```bash
   nano ~/.pretty-release-notes/config.toml
   ```

3. Map your `.env` variables to TOML sections:
   ```toml
   # .env: GH_TOKEN → TOML:
   [github]
   token = "your_token_here"

   # .env: OPENAI_API_KEY → TOML:
   [openai]
   api_key = "your_key_here"
   ```

**No migration needed if:**
- Your application uses the Library API with programmatic configuration
- You're passing configuration via `DictConfigLoader`
- You want to continue using `.env` (still supported via `EnvConfigLoader`)

#### Moving Existing Database Files

If you have existing database files in your project directory and want to preserve your cached release note summaries, follow these steps:

**For SQLite databases (default):**
```bash
# Create the new directory if it doesn't exist
mkdir -p ~/.pretty-release-notes

# Move your existing database file
mv /path/to/your/project/stored_lines.sqlite ~/.pretty-release-notes/

# Or if your database has a custom name
mv /path/to/your/project/your_db_name.sqlite ~/.pretty-release-notes/
```

**For CSV databases:**
```bash
# Create the new directory if it doesn't exist
mkdir -p ~/.pretty-release-notes

# Move your existing CSV file
mv /path/to/your/project/stored_lines.csv ~/.pretty-release-notes/
```

**Alternatively, continue using your old location:**

If you prefer to keep your database in its current location, you can specify an absolute path in your configuration:

```toml
# In config.toml
[database]
name = "/absolute/path/to/your/database/stored_lines"
```

Or in `.env` (legacy):
```bash
DB_NAME=/absolute/path/to/your/database/stored_lines
```

The tool will automatically detect absolute paths and use them as-is.

#### Why This Change?

1. **Cleaner separation**: User data is separated from application code
2. **Platform conventions**: Follows standard practice for user data storage
3. **No permission issues**: User home directory is always writable
4. **Multi-user support**: Each user can maintain their own cache
5. **Version control safe**: No risk of accidentally committing database files

#### Configuration Reference

The `DB_NAME` configuration variable now behaves as follows:

- **Relative path** (default): `DB_NAME=stored_lines` → `~/.pretty-release-notes/stored_lines.sqlite`
- **Absolute path**: `DB_NAME=/var/cache/prn/db` → `/var/cache/prn/db.sqlite`

No changes are required to existing configuration files. The default behavior has simply changed to use the user directory.
