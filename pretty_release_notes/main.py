#!/usr/bin/env python
"""Pretty Release Notes CLI."""

import time
from pathlib import Path

import typer

from .adapters.cli_progress import CLIProgressReporter
from .core.config_loader import TomlConfigLoader
from .generator import ReleaseNotesGenerator
from .setup_command import setup_config
from .ui import CLI

app = typer.Typer(
	help="Transform GitHub release notes with AI",
	invoke_without_command=True,
	no_args_is_help=True,
)


@app.callback()
def callback():
	"""Transform GitHub release notes with AI."""
	pass


@app.command()
def generate(
	repo: str,
	tag: str,
	owner: str | None = None,
	database: bool = True,
	prompt_path: Path | None = None,
	force_use_commits: bool = False,
	group_by_type: bool = False,
	config_path: Path | None = None,
):
	"""Generate pretty release notes for a GitHub repository.

	Configuration is loaded from ~/.pretty-release-notes/config.toml by default.
	Use --config-path to specify a different location.
	"""
	start_time = time.time()

	# Load base config from TOML
	loader = TomlConfigLoader(config_path)
	config = loader.load()

	# Override with CLI arguments
	if owner:
		config.github.owner = owner
	if prompt_path:
		config.prompt_path = prompt_path
	config.database.enabled = database
	config.force_use_commits = force_use_commits
	if group_by_type:
		config.grouping.group_by_type = True

	# Create UI and adapter
	cli = CLI()
	progress_reporter = CLIProgressReporter(cli)

	# Determine the owner to use
	repo_owner = owner or config.github.owner
	if not repo_owner:
		raise ValueError("Owner must be specified either via --owner flag or DEFAULT_OWNER in .env")

	# Create generator with config
	generator = ReleaseNotesGenerator(config, progress_reporter)
	generator.initialize_repository(repo_owner, repo)
	notes = generator.generate(tag)
	cli.show_release_notes("New Release Notes", notes)
	end_time = time.time()
	cli.show_success(f"Generated release notes in {end_time - start_time:.2f} seconds total.")

	if cli.confirm_update():
		generator.update_on_github(notes, tag)


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
	"""Interactive setup to create or update configuration file.

	This command walks you through creating a configuration file with
	interactive prompts. Use --migrate-env to read values from an existing
	.env file (useful for one-time migration).
	"""
	setup_config(config_path=config_path, migrate_env=migrate_env)


if __name__ == "__main__":
	app()
