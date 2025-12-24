Turn GitHub's auto-generated release notes into human-readable sentences.

Go from this:

![Original](img/original.png)

To this:

![Modified](img/modified.png)

## Features

- **AI-Powered Summaries** - Converts technical PR titles into clear, user-friendly sentences
- **Smart Filtering** - Automatically excludes non-user-facing changes (chore, ci, refactor, test, style)
- **Revert Detection** - Automatically filters out PRs that were reverted within the same release
- **Backport Intelligence** - Reuses summaries from original PRs for backports, maintaining consistency
- **Author & Reviewer Attribution** - Credits human contributors while excluding bots
- **Intelligent Caching** - Stores generated summaries to avoid redundant API calls and reduce costs
- **Grouped Release Notes** - Optional grouping by conventional commit type (Features, Bug Fixes, Performance, etc.)
- **Multi-Mode Architecture** - Use as CLI tool, Python library, or REST API backend
- **Rich Context** - Incorporates PR descriptions, linked issues, and code diffs for accurate summaries
- **Interactive Setup** - Guided configuration with validation and migration from legacy formats

> [!NOTE]
> The default prompt is geared towards [ERPNext](https://github.com/frappe/erpnext) and the [Frappe Framework](https://github.com/frappe/frappe). If you want to use this for different projects, set your own `prompt_path` in `config.toml`.

## Configuration

### Interactive Setup (Recommended)

The easiest way to configure the tool is using the interactive setup command:

```bash
pretty-release-notes setup
```

This will:
- Guide you through all configuration options with helpful prompts
- Show sane defaults for each setting
- Create the config file at `~/.pretty-release-notes/config.toml`

**First-time migration from .env?** Use the `--migrate-env` flag:
```bash
pretty-release-notes setup --migrate-env
```
This will read your existing `.env` file and suggest those values as defaults.

### Manual Setup

Alternatively, copy `config.toml.example` to `~/.pretty-release-notes/config.toml` and fill in your credentials:

```bash
# Create config directory
mkdir -p ~/.pretty-release-notes

# Copy example config
cp config.toml.example ~/.pretty-release-notes/config.toml

# Edit with your credentials
nano ~/.pretty-release-notes/config.toml
```

### Configuration Format

The configuration file uses TOML format with sections for GitHub credentials, OpenAI settings, database caching, and filters. See [`config.toml.example`](config.toml.example) for the complete structure and all available options.

You can override the config location using the `--config-path` flag.

## Installation

```bash
# Clone the repository
git clone https://github.com/barredterra/pretty_release_notes
cd pretty_release_notes

# Create virtual environment and install
python -m venv env
source env/bin/activate
pip install -e .
```

## Usage

### CLI

After installation, you can use the CLI in several ways:

```bash
# View all commands
pretty-release-notes --help

# Generate release notes
pretty-release-notes generate erpnext v15.38.4  # using owner from config.toml
pretty-release-notes generate --owner alyf-de banking v0.0.1

# Use a custom config file
pretty-release-notes generate --config-path /path/to/config.toml erpnext v15.38.4

# Specify custom comparison range
pretty-release-notes generate erpnext v15.38.4 --previous-tag v15.38.0
```

Example output:

```markdown
---- Original ----
## What's Changed
* fix: list view and form status not same for purchase order (backport #43690) (backport #43692) by @mergify in https://github.com/frappe/erpnext/pull/43706


**Full Changelog**: https://github.com/frappe/erpnext/compare/v15.38.3...v15.38.4

---- Modified ----
## What's Changed
* Removes unnecessary decimal precision checks for _per_received_ and _per_billed_ fields in **Purchase Order**, so the list view status and form status remain consistent. https://github.com/frappe/erpnext/pull/43706


**Full Changelog**: https://github.com/frappe/erpnext/compare/v15.38.3...v15.38.4
**Authors**: @rohitwaghchaure
```

### Library Usage

You can also use `pretty_release_notes` as a Python library in your own projects:

```python
from pretty_release_notes import ReleaseNotesBuilder

# Build a client with configuration
client = (
    ReleaseNotesBuilder()
    .with_github_token("ghp_your_token")
    .with_openai("sk_your_key", model="gpt-4")
    .with_database("sqlite", enabled=True)
    .with_filters(
        exclude_types={"chore", "ci", "refactor"},
        exclude_labels={"skip-release-notes"},
    )
    .build()
)

# Generate release notes
notes = client.generate_release_notes(
    owner="frappe",
    repo="erpnext",
    tag="v15.38.4",
    previous_tag_name="v15.38.0",  # Optional: custom comparison range
)
print(notes)

# Optionally update on GitHub
client.update_github_release("frappe", "erpnext", "v15.38.4", notes)
```

For more examples, see [`examples/library_usage.py`](examples/library_usage.py).

### Web API

The tool can also be run as a REST API server for integration with web frontends.

#### Starting the Server

First, install the web dependencies:

```bash
source env/bin/activate
pip install -e .[web]
```

Then start the server:

```bash
# Using uvicorn directly
python -m uvicorn pretty_release_notes.web.app:app --host 0.0.0.0 --port 8000

# Or using the provided server script
python -m pretty_release_notes.web.server
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

#### API Endpoints

**Health Check**
```bash
curl http://localhost:8000/health
```

**Create Release Notes Job**
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "frappe",
    "repo": "erpnext",
    "tag": "v15.38.4",
    "previous_tag_name": "v15.38.0",
    "github_token": "ghp_your_token_here",
    "openai_key": "sk-your_key_here",
    "openai_model": "gpt-4",
    "exclude_types": ["chore", "ci", "refactor"],
    "exclude_labels": ["skip-release-notes"],
    "exclude_authors": ["dependabot[bot]"]
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2025-01-19T10:30:00.000000"
}
```

**Check Job Status**
```bash
curl http://localhost:8000/jobs/{job_id}
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-01-19T10:30:00.000000",
  "completed_at": "2025-01-19T10:30:15.000000",
  "result": "## What's Changed\n* Fixed bug...",
  "progress": [
    {
      "timestamp": "2025-01-19T10:30:05.000000",
      "type": "success",
      "message": "Downloaded PRs in 0.42 seconds."
    }
  ],
  "error": null
}
```

## Authors and Reviewers

The authors and reviewers of the PRs are added to the release notes.

- An author who reviewed or merged their own PR or backport is not a reviewer.
- A non-author who reviewed or merged someone else's PR is a reviewer.
- The author of the original PR is also the author of the backport.

## Backports

We try to use the same message for backports as for the original PR. For this, we look for `(backport #<number>)` _at the end_ of the PR title and check if we have existing messages for that PR in our database. If we do, we use the message for the original PR. If we don't, we create a new message for the backport.

This means that backports of backports are currently not supported / will get a new message. To get the same message, PRs must be a direct backport of the original PR.

## Testing

Run the full test suite:

```bash
pytest tests/
```

Run specific test files:

```bash
pytest tests/test_web_api.py      # Web API tests
pytest tests/test_core.py          # Core configuration tests
pytest tests/test_execution.py     # Concurrent execution tests
```

The test suite includes:
- **Core abstractions** - Configuration, progress reporting, execution strategies
- **Web API** - All REST endpoints, concurrent requests, error handling
- **Database threading** - Thread-safe operations under load
- **API client** - Library usage patterns

All tests use mocks to avoid actual API calls, making them fast and reliable.
