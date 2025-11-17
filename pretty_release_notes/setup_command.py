"""Interactive setup command for creating/updating configuration."""

from pathlib import Path

import typer
from dotenv import dotenv_values
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()


def setup_config(
	config_path: Path | None = None,
	migrate_env: bool = False,
) -> None:
	"""Interactive setup to create or update configuration file.

	Args:
		config_path: Path to config file. If None, uses default location.
		migrate_env: If True, attempts to read values from .env file. Default False.
	"""
	# Determine config path
	if config_path is None:
		config_path = Path.home() / ".pretty-release-notes" / "config.toml"

	# Check if config already exists
	config_exists = config_path.exists()
	if config_exists:
		console.print(f"\n[yellow]Configuration file already exists at:[/yellow] {config_path}")
		if not Confirm.ask("Do you want to update it?", default=False):
			console.print("[dim]Setup cancelled.[/dim]")
			return
		console.print()

	# Try to load existing values
	existing_values = {}

	# Try to read from existing TOML config
	if config_exists:
		try:
			import tomllib

			with open(config_path, "rb") as f:
				toml_config = tomllib.load(f)
			existing_values = _flatten_toml(toml_config)
			console.print("[green]✓[/green] Loaded existing values from TOML config")
		except Exception as e:
			console.print(f"[yellow]Warning: Could not read existing config: {e}[/yellow]")

	# Try to migrate from .env file
	env_path = Path.cwd() / ".env"
	if migrate_env and env_path.exists() and not existing_values:
		try:
			env_values = dotenv_values(env_path)
			existing_values = _migrate_env_to_dict(env_values)
			console.print(f"[green]✓[/green] Found .env file with existing values at {env_path}")
		except Exception as e:
			console.print(f"[yellow]Warning: Could not read .env file: {e}[/yellow]")

	if existing_values:
		console.print("[dim]Existing values will be shown as defaults (press Enter to keep them)[/dim]\n")

	# Collect configuration values
	console.print("[bold cyan]GitHub Configuration[/bold cyan]")
	github_token = Prompt.ask(
		"GitHub Personal Access Token",
		default=existing_values.get("github_token", ""),
		password=True,
	)
	github_owner = Prompt.ask(
		"Default Repository Owner (optional)",
		default=existing_values.get("github_owner") or "frappe",
	)

	console.print("\n[bold cyan]OpenAI Configuration[/bold cyan]")
	openai_key = Prompt.ask(
		"OpenAI API Key",
		default=existing_values.get("openai_key", ""),
		password=True,
	)
	openai_model = Prompt.ask(
		"OpenAI Model",
		default=existing_values.get("openai_model") or "o1",
	)
	max_patch_size = Prompt.ask(
		"Maximum patch size before fallback",
		default=str(existing_values.get("max_patch_size", 10000)),
	)

	console.print("\n[bold cyan]Database Configuration[/bold cyan]")
	db_type = Prompt.ask(
		"Database type",
		choices=["sqlite", "csv"],
		default=existing_values.get("db_type") or "sqlite",
	)
	db_name = Prompt.ask(
		"Database name (without extension)",
		default=existing_values.get("db_name") or "stored_lines",
	)
	db_enabled = Confirm.ask(
		"Enable caching?",
		default=existing_values.get("db_enabled", True),
	)

	console.print("\n[bold cyan]Filter Configuration[/bold cyan]")
	exclude_types = Prompt.ask(
		"PR/commit types to exclude (comma-separated)",
		default=existing_values.get("exclude_types") or "chore,refactor,ci,style,test",
	)
	exclude_labels = Prompt.ask(
		"PR labels to exclude (comma-separated)",
		default=existing_values.get("exclude_labels") or "skip-release-notes",
	)
	exclude_authors = Prompt.ask(
		"Authors to exclude (comma-separated)",
		default=(
			existing_values.get("exclude_authors")
			or "mergify[bot],copilot-pull-request-reviewer[bot],coderabbitai[bot],dependabot[bot],cursor[bot]"
		),
	)

	console.print("\n[bold cyan]Output Grouping[/bold cyan]")
	group_by_type = Confirm.ask(
		"Group release notes by conventional commit type?",
		default=existing_values.get("group_by_type", False),
	)

	# Build TOML content
	toml_content = _build_toml_content(
		github_token=github_token,
		github_owner=github_owner,
		openai_key=openai_key,
		openai_model=openai_model,
		max_patch_size=int(max_patch_size),
		db_type=db_type,
		db_name=db_name,
		db_enabled=db_enabled,
		exclude_types=exclude_types,
		exclude_labels=exclude_labels,
		exclude_authors=exclude_authors,
		group_by_type=group_by_type,
	)

	# Confirm before writing
	console.print(f"\n[bold]Configuration will be written to:[/bold] {config_path}")
	console.print("\n[dim]Preview:[/dim]")
	console.print("[dim]" + "─" * 60 + "[/dim]")
	# Mask sensitive values in preview
	preview = toml_content.replace(github_token, "ghp_***" if github_token else "")
	preview = preview.replace(openai_key, "sk-***" if openai_key else "")
	# Escape opening square brackets for Rich markup (closing brackets are fine)
	preview = preview.replace("[", r"\[")
	console.print(preview)
	console.print("[dim]" + "─" * 60 + "[/dim]\n")

	if not Confirm.ask("Write this configuration?", default=True):
		console.print("[dim]Setup cancelled.[/dim]")
		return

	# Create directory if needed
	config_path.parent.mkdir(parents=True, exist_ok=True)

	# Write config file
	config_path.write_text(toml_content)
	console.print(f"\n[green]✓ Configuration saved to {config_path}[/green]")

	# Suggest removing .env if it was migrated
	if migrate_env and env_path.exists() and not config_exists:
		console.print(f"\n[yellow]Note:[/yellow] You can now remove the old .env file: {env_path}")
		if Confirm.ask("Delete .env file?", default=False):
			env_path.unlink()
			console.print(f"[green]✓ Deleted {env_path}[/green]")


def _flatten_toml(toml_config: dict) -> dict:
	"""Flatten nested TOML config to simple dict for defaults."""
	flat = {}

	github = toml_config.get("github", {})
	flat["github_token"] = github.get("token", "")
	flat["github_owner"] = github.get("owner", "")

	openai = toml_config.get("openai", {})
	flat["openai_key"] = openai.get("api_key", "")
	flat["openai_model"] = openai.get("model", "")
	flat["max_patch_size"] = openai.get("max_patch_size", 10000)

	database = toml_config.get("database", {})
	flat["db_type"] = database.get("type", "")
	flat["db_name"] = database.get("name", "")
	flat["db_enabled"] = database.get("enabled", True)

	filters = toml_config.get("filters", {})
	flat["exclude_types"] = ",".join(filters.get("exclude_change_types", []))
	flat["exclude_labels"] = ",".join(filters.get("exclude_change_labels", []))
	flat["exclude_authors"] = ",".join(filters.get("exclude_authors", []))

	grouping = toml_config.get("grouping", {})
	flat["group_by_type"] = grouping.get("group_by_type", False)

	return flat


def _migrate_env_to_dict(env_values: dict) -> dict:
	"""Convert .env format to dict for defaults."""
	return {
		"github_token": env_values.get("GH_TOKEN", ""),
		"github_owner": env_values.get("DEFAULT_OWNER", ""),
		"openai_key": env_values.get("OPENAI_API_KEY", ""),
		"openai_model": env_values.get("OPENAI_MODEL", ""),
		"max_patch_size": int(env_values.get("MAX_PATCH_SIZE", "10000")),
		"db_type": env_values.get("DB_TYPE", ""),
		"db_name": env_values.get("DB_NAME", ""),
		"db_enabled": True,
		"exclude_types": env_values.get("EXCLUDE_PR_TYPES", ""),
		"exclude_labels": env_values.get("EXCLUDE_PR_LABELS", ""),
		"exclude_authors": env_values.get("EXCLUDE_AUTHORS", ""),
	}


def _build_toml_content(
	github_token: str,
	github_owner: str,
	openai_key: str,
	openai_model: str,
	max_patch_size: int,
	db_type: str,
	db_name: str,
	db_enabled: bool,
	exclude_types: str,
	exclude_labels: str,
	exclude_authors: str,
	group_by_type: bool,
) -> str:
	"""Build TOML file content from values."""

	# Parse comma-separated strings to TOML arrays
	def to_toml_array(s: str) -> str:
		if not s.strip():
			return "[]"
		items = [f'"{item.strip()}"' for item in s.split(",") if item.strip()]
		return "[" + ", ".join(items) + "]"

	return f"""# Pretty Release Notes Configuration
# Generated by: pretty-release-notes setup

# Optional top-level settings
# Path to custom AI prompt template (default: "prompt.txt" in current directory)
# prompt_path = "prompt.txt"

# Force using commits even when PRs are available (default: false)
# force_use_commits = false

[github]
token = "{github_token}"
owner = "{github_owner}"

[openai]
api_key = "{openai_key}"
model = "{openai_model}"
max_patch_size = {max_patch_size}

[database]
type = "{db_type}"
name = "{db_name}"
enabled = {str(db_enabled).lower()}

[filters]
exclude_change_types = {to_toml_array(exclude_types)}
exclude_change_labels = {to_toml_array(exclude_labels)}
exclude_authors = {to_toml_array(exclude_authors)}

[grouping]
group_by_type = {str(group_by_type).lower()}
# Customize type headings by editing the config file directly
# type_headings = {{ feat = "Features", fix = "Bug Fixes" }}
# other_heading = "Other Changes"
"""


# CLI command
app = typer.Typer()


@app.command()
def setup(
	config_path: Path | None = typer.Option(
		None,
		"--config-path",
		help="Path to config file (default: ~/.pretty-release-notes/config.toml)",
	),
	migrate_env: bool = typer.Option(
		False,
		"--migrate-env",
		help="Attempt to read and migrate values from .env file",
	),
) -> None:
	"""Interactive setup to create or update configuration file."""
	setup_config(config_path=config_path, migrate_env=migrate_env)


if __name__ == "__main__":
	app()
