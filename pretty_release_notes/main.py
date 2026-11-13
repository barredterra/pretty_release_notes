#!/usr/bin/env python
"""Pretty Release Notes CLI."""

import json
import time
import tomllib
from fnmatch import fnmatch
from pathlib import Path
from typing import Annotated

import typer

from .adapters.cli_progress import CLIProgressReporter
from .core.config import ReleaseNotesConfig
from .core.config_loader import TomlConfigLoader
from .generator import ReleaseNotesGenerator
from .github_client import GitHubClient
from .labeler import label_release
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
	group_by_area: Annotated[
		bool, typer.Option("--group-by-area", help="Group by area, such as Accounts or Stock, and collapse large areas")
	] = False,
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
	if group_by_area:
		config.grouping.group_by_area = True

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


def _load_state() -> dict[str, dict[str, list[str]]]:
	"""Return {"processed": {repo: [tags]}, "labeled": {repo: [tags]}}."""
	if not STATE_FILE.exists():
		return {"processed": {}, "labeled": {}}

	raw = json.loads(STATE_FILE.read_text())
	if "processed" not in raw:
		# Old format: {repo: [tags]} with processed tags only. These releases are older than
		# the labeling feature, so mark them as labeled too. Else the next cycle comments on old PRs.
		raw = {"processed": raw, "labeled": {repo: list(tags) for repo, tags in raw.items()}}
	state: dict[str, dict[str, list[str]]] = {"processed": raw["processed"], "labeled": raw.get("labeled", {})}
	return state


def _save_state(state: dict[str, dict[str, list[str]]]) -> None:
	STATE_DIR.mkdir(parents=True, exist_ok=True)
	STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def _mark_done(tags_by_repo: dict[str, list[str]], repo_spec: str, tag: str) -> None:
	tags = tags_by_repo.get(repo_spec, [])
	tags_by_repo[repo_spec] = [tag, *tags][:50]


def _load_poll_config(config_path: Path) -> dict:
	with open(config_path, "rb") as f:
		raw = tomllib.load(f)
	poll_config: dict = raw.get("poll", {})
	return poll_config


def _load_poll_repos(config_path: Path) -> list[str]:
	repos: list[str] = _load_poll_config(config_path).get("repos", [])
	if not repos:
		raise typer.BadParameter("No repos configured. Add [poll] repos = [...] to your config file.")
	return repos


@app.command()
def poll(
	seed: bool = typer.Option(
		False, "--seed", help="Mark current releases as processed and labeled without changing them"
	),
	install_cron: bool = typer.Option(False, "--install-cron", help="Install a crontab entry to poll every 15 minutes"),
	config_path: Path | None = typer.Option(None, "--config-path", help="Path to config file"),
):
	"""Poll GitHub for new releases and generate notes automatically.

	Reads the list of repositories from [poll] repos in the config file.
	If [poll] release_label is set, also adds that label and a release comment to the PRs of each release.
	Run with --seed first to skip existing releases, then --install-cron to automate.
	"""
	loader = TomlConfigLoader(config_path)
	config = loader.load()
	repos = _load_poll_repos(loader.config_path)
	poll_config = _load_poll_config(loader.config_path)
	release_label: str | None = poll_config.get("release_label")
	exclude_tags: list[str] = poll_config.get("exclude_tags", [])
	github = GitHubClient(config.github.token)

	state = _load_state()

	if seed:
		for repo_spec in repos:
			owner, repo_name = repo_spec.split("/", 1)
			releases = github.list_releases(owner, repo_name)
			tags = [str(r["tag_name"]) for r in releases if not r.get("draft")]
			state["processed"][repo_spec] = tags
			state["labeled"][repo_spec] = tags
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
	labeling_stopped = False

	for repo_spec in repos:
		owner, repo_name = repo_spec.split("/", 1)

		try:
			releases = github.list_releases(owner, repo_name)
		except Exception as e:
			typer.echo(f"ERROR listing {repo_spec}: {e}", err=True)
			continue

		for release in releases:
			tag = str(release["tag_name"])
			is_excluded = any(fnmatch(tag, pattern) for pattern in exclude_tags)
			if release.get("draft") or is_excluded:
				continue

			# The two steps are independent: a failure in one does not repeat or block the other.
			if tag not in state["processed"].get(repo_spec, []):
				_update_release_notes(config, progress_reporter, state, owner, repo_name, tag)

			if release_label and not labeling_stopped and tag not in state["labeled"].get(repo_spec, []):
				# After a failure (for example a rate limit), stop labeling until the next cycle.
				labeling_stopped = not _label_release(github, state, owner, repo_name, tag, release_label)


def _update_release_notes(
	config: ReleaseNotesConfig,
	progress_reporter: CLIProgressReporter,
	state: dict[str, dict[str, list[str]]],
	owner: str,
	repo_name: str,
	tag: str,
) -> None:
	repo_spec = f"{owner}/{repo_name}"
	typer.echo(f"Processing {repo_spec} {tag}")
	try:
		generator = ReleaseNotesGenerator(config, progress_reporter)
		generator.initialize_repository(owner, repo_name)
		notes = generator.generate(tag)
		updated = generator.update_on_github(notes, tag)
	except Exception as e:
		typer.echo(f"FAILED {repo_spec} {tag}: {e}", err=True)
		return

	if not updated:
		# Leave the tag unprocessed so the next poll cycle retries it.
		# Summaries are cached, so the retry is cheap.
		typer.echo(f"FAILED {repo_spec} {tag}: GitHub rejected the update, will retry", err=True)
		return

	_mark_done(state["processed"], repo_spec, tag)
	_save_state(state)
	typer.echo(f"Done {repo_spec} {tag}")


def _label_release(
	github: GitHubClient,
	state: dict[str, dict[str, list[str]]],
	owner: str,
	repo_name: str,
	tag: str,
	label: str,
) -> bool:
	"""Return False if labeling failed."""
	repo_spec = f"{owner}/{repo_name}"
	typer.echo(f"Labeling PRs of {repo_spec} {tag}")
	try:
		repository = github.get_repository(owner, repo_name)
		label_release(github, repository, tag, label)
	except Exception as e:
		# Leave the tag unlabeled. The next poll cycle skips the PRs that have the label already.
		typer.echo(f"FAILED labeling {repo_spec} {tag}: {e}", err=True)
		return False

	_mark_done(state["labeled"], repo_spec, tag)
	_save_state(state)
	typer.echo(f"Labeled PRs of {repo_spec} {tag}")
	return True


@app.command()
def label(
	repo: str,
	tag: str,
	owner: str | None = None,
	label: str | None = typer.Option(None, "--label", help="Label to add (default: [poll] release_label)"),
	config_path: Path | None = typer.Option(None, "--config-path", help="Path to config file"),
):
	"""Add the release label and a release comment to each PR of a release.

	PRs that have the label already are skipped.
	"""
	loader = TomlConfigLoader(config_path)
	config = loader.load()
	label = label or _load_poll_config(loader.config_path).get("release_label")
	if not label:
		raise typer.BadParameter("No label given. Use --label or add [poll] release_label to your config file.")

	repo_owner = owner or config.github.owner
	if not repo_owner:
		raise typer.BadParameter("Owner must be specified either via --owner or [github] owner in the config file.")

	github = GitHubClient(config.github.token)
	repository = github.get_repository(repo_owner, repo)
	label_release(github, repository, tag, label)
	typer.echo(f"Labeled PRs of {repo_owner}/{repo} {tag}")


if __name__ == "__main__":
	app()
