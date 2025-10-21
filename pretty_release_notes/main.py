#!/usr/bin/env python
"""Pretty Release Notes CLI - Backward compatible entry point."""

import time
from pathlib import Path

import typer

from .adapters.cli_progress import CLIProgressReporter
from .core.config_loader import EnvConfigLoader
from .generator import ReleaseNotesGenerator
from .ui import CLI

app = typer.Typer()


@app.command()
def main(
	repo: str,
	tag: str,
	owner: str | None = None,
	database: bool = True,
	prompt_path: Path | None = None,
	force_use_commits: bool = False,
):
	"""Generate pretty release notes for a GitHub repository.

	This command maintains full backward compatibility with the original CLI.
	"""
	start_time = time.time()

	# Load base config from .env
	loader = EnvConfigLoader()
	config = loader.load()

	# Override with CLI arguments
	if owner:
		config.github.owner = owner
	if prompt_path:
		config.prompt_path = prompt_path
	config.database.enabled = database
	config.force_use_commits = force_use_commits

	# Create UI and adapter
	cli = CLI()
	progress_reporter = CLIProgressReporter(cli)

	# Create generator with config
	generator = ReleaseNotesGenerator(config, progress_reporter)
	generator.initialize_repository(config.github.owner or owner, repo)
	notes = generator.generate(tag)
	cli.show_release_notes("New Release Notes", notes)
	end_time = time.time()
	cli.show_success(f"Generated release notes in {end_time - start_time:.2f} seconds total.")

	if cli.confirm_update():
		generator.update_on_github(notes, tag)


if __name__ == "__main__":
	app()
