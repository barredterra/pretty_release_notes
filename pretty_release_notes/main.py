#!/usr/bin/env python
"""Pretty Release Notes CLI."""

import json
import time
import tomllib
from pathlib import Path
from typing import Annotated

import typer

from .adapters.cli_progress import CLIProgressReporter
from .core.config_loader import TomlConfigLoader
from .generator import ReleaseNotesGenerator
from .github_client import GitHubClient
from .openai_client import SUPPORTED_REASONING_EFFORTS, normalize_reasoning_effort
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
	previous_tag: str | None = None,
	no_database: Annotated[bool, typer.Option("--no-database", help="Skip cache reads and writes")] = False,
	no_db_read: Annotated[bool, typer.Option("--no-db-read", help="Skip reading cached summaries")] = False,
	no_db_write: Annotated[bool, typer.Option("--no-db-write", help="Skip writing new summaries to the cache")] = False,
	prompt_path: Path | None = None,
	force_use_commits: bool = False,
	group_by_type: bool = True,
	yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation and update release notes on GitHub"),
	config_path: Path | None = None,
	reasoning_effort: str | None = typer.Option(
		None,
		"--reasoning-effort",
		help=(f"Override reasoning effort for this run. Supported values: {', '.join(SUPPORTED_REASONING_EFFORTS)}"),
	),
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
	if no_database:
		config.database.enabled = False
	if no_db_read:
		config.database.read_enabled = False
	if no_db_write:
		config.database.write_enabled = False
	config.force_use_commits = force_use_commits
	if reasoning_effort is not None:
		config.llm.reasoning_effort = normalize_reasoning_effort(reasoning_effort)
	if not group_by_type:
		config.grouping.group_by_type = False

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
	notes = generator.generate(tag, previous_tag_name=previous_tag)
	cli.show_release_notes("New Release Notes", notes)
	end_time = time.time()
	cli.show_success(f"Generated release notes in {end_time - start_time:.2f} seconds total.")

	if yes or cli.confirm_update():
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


STATE_DIR = Path.home() / ".pretty-release-notes"
STATE_FILE = STATE_DIR / "processed_releases.json"


def _load_state() -> dict[str, list[str]]:
	if STATE_FILE.exists():
		result: dict[str, list[str]] = json.loads(STATE_FILE.read_text())
		return result
	return {}


def _save_state(state: dict[str, list[str]]) -> None:
	STATE_DIR.mkdir(parents=True, exist_ok=True)
	STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def _load_poll_repos(config_path: Path) -> list[str]:
	with open(config_path, "rb") as f:
		raw = tomllib.load(f)
	repos: list[str] = raw.get("poll", {}).get("repos", [])
	if not repos:
		raise typer.BadParameter("No repos configured. Add [poll] repos = [...] to your config file.")
	return repos


@app.command()
def poll(
	seed: bool = typer.Option(False, "--seed", help="Seed state with current releases without processing them"),
	install_cron: bool = typer.Option(False, "--install-cron", help="Install a crontab entry to poll every 15 minutes"),
	config_path: Path | None = typer.Option(None, "--config-path", help="Path to config file"),
):
	"""Poll GitHub for new releases and generate notes automatically.

	Reads the list of repositories from [poll] repos in the config file.
	Run with --seed first to skip existing releases, then --install-cron to automate.
	"""
	loader = TomlConfigLoader(config_path)
	config = loader.load()
	repos = _load_poll_repos(loader.config_path)
	github = GitHubClient(config.github.token)

	state = _load_state()

	if seed:
		for repo_spec in repos:
			owner, repo_name = repo_spec.split("/", 1)
			releases = github.list_releases(owner, repo_name)
			tags = [str(r["tag_name"]) for r in releases if not r.get("draft")]
			state[repo_spec] = tags
			typer.echo(f"Seeded {repo_spec}: {', '.join(tags)}")
		_save_state(state)

	if install_cron:
		import shutil
		import subprocess

		exe = shutil.which("pretty-release-notes")
		if not exe:
			raise typer.BadParameter("pretty-release-notes not found in PATH")

		cmd = f"{exe} poll"
		if config_path:
			cmd += f" --config-path {config_path}"

		log_file = STATE_DIR / "poll.log"
		cron_line = f"*/15 * * * * {cmd} >> {log_file} 2>&1"

		result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
		existing = result.stdout if result.returncode == 0 else ""

		if "pretty-release-notes poll" in existing:
			typer.echo("Cron entry already exists.")
		else:
			new_crontab = existing.rstrip("\n") + "\n" + cron_line + "\n"
			subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
			typer.echo(f"Installed: {cron_line}")

	if seed or install_cron:
		return

	# One poll cycle
	cli = CLI()
	progress_reporter = CLIProgressReporter(cli)

	for repo_spec in repos:
		owner, repo_name = repo_spec.split("/", 1)

		try:
			releases = github.list_releases(owner, repo_name)
		except Exception as e:
			typer.echo(f"ERROR listing {repo_spec}: {e}", err=True)
			continue

		processed = state.get(repo_spec, [])

		for release in releases:
			if release.get("draft"):
				continue

			tag = str(release["tag_name"])
			if tag in processed:
				continue

			typer.echo(f"Processing {repo_spec} {tag}")

			try:
				generator = ReleaseNotesGenerator(config, progress_reporter)
				generator.initialize_repository(owner, repo_name)
				notes = generator.generate(tag)
				generator.update_on_github(notes, tag)

				processed.insert(0, tag)
				state[repo_spec] = processed[:50]
				_save_state(state)

				typer.echo(f"Done {repo_spec} {tag}")
			except Exception as e:
				typer.echo(f"FAILED {repo_spec} {tag}: {e}", err=True)


if __name__ == "__main__":
	app()
