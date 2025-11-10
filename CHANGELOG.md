# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Database Storage Location**: Database files are now stored in `~/.pretty-release-notes/` by default instead of the project directory. This provides better separation between user data and application code, follows platform conventions, and avoids permission issues.

### Migration Guide

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

```bash
# In your .env file
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
