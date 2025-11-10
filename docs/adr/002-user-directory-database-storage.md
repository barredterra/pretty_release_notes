# ADR 002: User Directory Database Storage

## Status
Accepted

## Date
2025-11-10

## Context
Previously, database files (SQLite and CSV) were stored in the project directory alongside the code. This approach had several issues:

1. **Data/Code Mixing**: Database files containing cached release note summaries were stored alongside application code, violating separation of concerns
2. **Version Control Pollution**: Database files could accidentally be committed to version control
3. **Permission Issues**: In system-wide installations, writing to the application directory might require elevated permissions
4. **Multi-User Conflicts**: Multiple users on the same system couldn't maintain separate caches
5. **Platform Conventions**: Not following platform-specific conventions for user data storage

## Decision
We changed the default database storage location from the project directory to `~/.pretty-release-notes/` in the user's home directory.

### Implementation Details

**Modified `pretty_release_notes/database.py`:**
- The `get_db()` factory function now checks if the provided path is relative or absolute
- Relative paths (default): Stored in `~/.pretty-release-notes/` directory
- Absolute paths: Stored at the exact location specified
- Directory is automatically created if it doesn't exist using `Path.mkdir(parents=True, exist_ok=True)`

**Path Resolution Logic:**
```python
def get_db(db_type: str, db_name: str) -> Database:
    db_path = Path(db_name)

    # If path is relative (not absolute), use ~/.pretty-release-notes/ as base directory
    if not db_path.is_absolute():
        base_dir = Path.home() / ".pretty-release-notes"
        base_dir.mkdir(parents=True, exist_ok=True)
        db_path = base_dir / db_name

    # ... rest of implementation
```

### Configuration Behavior

- **Default**: `DB_NAME=stored_lines` → `~/.pretty-release-notes/stored_lines.sqlite`
- **Custom relative**: `DB_NAME=my_cache` → `~/.pretty-release-notes/my_cache.sqlite`
- **Absolute path**: `DB_NAME=/var/cache/prn/db` → `/var/cache/prn/db.sqlite`

### Backward Compatibility

Users who previously had database files in their project directory will need to:
1. Move existing database files to `~/.pretty-release-notes/` to preserve cached summaries
2. Or continue using absolute paths pointing to their old location

No breaking changes to the API or configuration format.

## Consequences

### Positive

1. **Clean Separation**: User data is separated from application code
2. **Platform Convention**: Follows standard practice for user data storage (similar to `.cache`, `.config` directories)
3. **No Permission Issues**: User home directory is always writable by the user
4. **Multi-User Support**: Each user maintains their own cache
5. **Version Control Safe**: No risk of accidentally committing database files from default location
6. **Project Directory Clean**: Development and installed versions don't clutter the project directory

### Negative

1. **Migration Required**: Existing users need to manually move database files to preserve cached data
2. **Discoverability**: Database files are now hidden in a dot-directory (though this is also an advantage for most users)
3. **Cross-Platform Concerns**: `Path.home()` behavior may vary slightly across platforms, though it's well-supported

### Neutral

1. **Testing**: Tests continue to work as they use temporary directories or in-memory databases
2. **Configuration**: No changes to configuration format; existing `.env` files continue to work
3. **Absolute Paths**: Power users can still use absolute paths if they prefer a different location

## Alternatives Considered

### 1. Platform-Specific Directories
Use platform-specific directories like:
- Linux: `~/.local/share/pretty-release-notes/`
- macOS: `~/Library/Application Support/pretty-release-notes/`
- Windows: `%APPDATA%\pretty-release-notes\`

**Rejected because**: Added complexity for a simple caching use case. The hidden directory pattern (`~/.app-name`) is simpler and universally understood.

### 2. XDG Base Directory Specification
Follow XDG standard: `${XDG_DATA_HOME}/pretty-release-notes/` or `~/.local/share/pretty-release-notes/`

**Rejected because**: While more "correct" on Linux, it's less intuitive for macOS/Windows users and adds complexity. The tool is cross-platform and used by developers familiar with dot-directories.

### 3. Keep Current Location as Default
Maintain project directory as default, only use user directory when explicitly configured.

**Rejected because**: Doesn't solve the fundamental problem of data/code mixing. Would require users to actively opt into the better behavior.

### 4. Automatic Migration on First Run
Automatically detect and move old database files on first run.

**Rejected because**:
- Adds complexity to the initialization code
- Surprising behavior (moving user files)
- Could cause issues if multiple versions are installed
- Manual migration is straightforward and explicit
