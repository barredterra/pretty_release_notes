import json
from unittest.mock import patch

from requests import HTTPError
from typer.testing import CliRunner

from pretty_release_notes.core.config import DatabaseConfig, GitHubConfig, LLMConfig, ReleaseNotesConfig
from pretty_release_notes.main import app
from pretty_release_notes.models.repository import Repository

runner = CliRunner()


class TestMainCLI:
	def _config(self, database: DatabaseConfig | None = None) -> ReleaseNotesConfig:
		return ReleaseNotesConfig(
			github=GitHubConfig(token="gh-token", owner="frappe"),
			llm=LLMConfig(api_key="llm-key"),
			database=database,
		)

	def _run_generate_with_config(self, config: ReleaseNotesConfig, extra_args: list[str] | None = None):
		with (
			patch("pretty_release_notes.main.TomlConfigLoader") as mock_loader_class,
			patch("pretty_release_notes.main.ReleaseNotesGenerator") as mock_generator_class,
			patch("pretty_release_notes.main.CLI") as mock_cli_class,
		):
			mock_loader_class.return_value.load.return_value = config
			mock_generator = mock_generator_class.return_value
			mock_generator.generate.return_value = "# Notes"
			mock_cli = mock_cli_class.return_value
			mock_cli.confirm_update.return_value = False

			return runner.invoke(
				app,
				["generate", "erpnext", "v1.0.0", *(extra_args or [])],
			)

	def test_generate_accepts_reasoning_effort_override(self):
		config = self._config()

		with (
			patch("pretty_release_notes.main.TomlConfigLoader") as mock_loader_class,
			patch("pretty_release_notes.main.ReleaseNotesGenerator") as mock_generator_class,
			patch("pretty_release_notes.main.CLI") as mock_cli_class,
		):
			mock_loader_class.return_value.load.return_value = config
			mock_generator = mock_generator_class.return_value
			mock_generator.generate.return_value = "# Notes"
			mock_cli = mock_cli_class.return_value
			mock_cli.confirm_update.return_value = False

			result = runner.invoke(
				app,
				["generate", "erpnext", "v1.0.0", "--reasoning-effort", "high"],
			)

		assert result.exit_code == 0, result.output
		assert config.llm.reasoning_effort == "high"
		mock_generator_class.assert_called_once()
		mock_generator.initialize_repository.assert_called_once_with("frappe", "erpnext")
		mock_generator.generate.assert_called_once_with("v1.0.0", previous_tag_name=None)

	def test_generate_preserves_database_config_without_cli_override(self):
		config = self._config(database=DatabaseConfig(enabled=False))

		result = self._run_generate_with_config(config)

		assert result.exit_code == 0, result.output
		assert config.database.read_enabled is False
		assert config.database.write_enabled is False

	def test_generate_no_database_disables_read_and_write(self):
		config = self._config()

		result = self._run_generate_with_config(config, ["--no-database"])

		assert result.exit_code == 0, result.output
		assert config.database.read_enabled is False
		assert config.database.write_enabled is False

	def test_generate_no_db_read_only_disables_cache_reads(self):
		config = self._config()

		result = self._run_generate_with_config(config, ["--no-db-read"])

		assert result.exit_code == 0, result.output
		assert config.database.read_enabled is False
		assert config.database.write_enabled is True

	def test_generate_no_db_write_only_disables_cache_writes(self):
		config = self._config()

		result = self._run_generate_with_config(config, ["--no-db-write"])

		assert result.exit_code == 0, result.output
		assert config.database.read_enabled is True
		assert config.database.write_enabled is False

	def test_generate_rejects_invalid_reasoning_effort(self):
		config = self._config()

		with patch("pretty_release_notes.main.TomlConfigLoader") as mock_loader_class:
			mock_loader_class.return_value.load.return_value = config
			result = runner.invoke(
				app,
				["generate", "erpnext", "v1.0.0", "--reasoning-effort", "maximum"],
			)

		assert result.exit_code == 1
		assert isinstance(result.exception, ValueError)
		assert "Invalid reasoning effort" in str(result.exception)


class FakeGitHub:
	"""Fake GitHubClient with releases, generated notes, PR labels and comments."""

	def __init__(self, prs_by_tag: dict[str, list[int]], labels: dict[int, set[str]] | None = None):
		self.prs_by_tag = prs_by_tag
		self.labels = labels or {}
		self.comments: list[tuple[int, str]] = []
		self.generated: list[tuple[str, str | None]] = []
		self.write_limit: int | None = None
		self.writes = 0

	def list_releases(self, owner: str, repo: str) -> list[dict]:
		return [{"tag_name": tag} for tag in self.prs_by_tag]

	def get_repository(self, owner: str, name: str) -> Repository:
		return Repository(
			owner=owner,
			name=name,
			url=f"https://api.github.com/repos/{owner}/{name}",
			html_url=f"https://github.com/{owner}/{name}",
		)

	def get_release(self, repository: Repository, tag: str) -> dict:
		return {"body": f"**Full Changelog**: https://github.com/owner/repo/compare/v0.9.0...{tag}"}

	def generate_release_notes(self, repository: Repository, tag: str, previous_tag_name: str | None) -> dict:
		self.generated.append((tag, previous_tag_name))
		lines = [f"* fix: change {n} by @dev in https://github.com/owner/repo/pull/{n}" for n in self.prs_by_tag[tag]]
		return {"body": "## What's Changed\n" + "\n".join(lines)}

	def get_pr_labels(self, repository: Repository, pr_numbers: list[int]) -> dict[int, set[str]]:
		return {n: set(self.labels.get(n, set())) for n in pr_numbers}

	def _write(self) -> None:
		if self.write_limit is not None and self.writes >= self.write_limit:
			raise HTTPError("403 Client Error: You have exceeded a secondary rate limit")
		self.writes += 1

	def add_comment(self, repository: Repository, issue_no: int, body: str) -> None:
		self._write()
		self.comments.append((issue_no, body))

	def add_labels(self, repository: Repository, issue_no: int, labels: list[str]) -> None:
		self._write()
		self.labels.setdefault(issue_no, set()).update(labels)

	def commented_prs(self) -> list[int]:
		return [pr_no for pr_no, _ in self.comments]


class TestPollCLI:
	"""Run the poll CLI with a real config file, a temp state file and a fake GitHub client."""

	def _write_config(self, tmp_path, release_label: str | None = None):
		config_file = tmp_path / "config.toml"
		label_line = f'release_label = "{release_label}"' if release_label else ""
		config_file.write_text(
			f"""
[github]
token = "gh-token"

[llm]
api_key = "llm-key"

[poll]
repos = ["owner/repo"]
{label_line}
"""
		)
		return config_file

	def _run_poll(
		self, tmp_path, github: FakeGitHub, update_succeeds: bool = True, extra_args: list[str] | None = None
	):
		config_file = tmp_path / "config.toml"
		state_file = tmp_path / "processed_releases.json"

		with (
			patch("pretty_release_notes.main.STATE_DIR", tmp_path),
			patch("pretty_release_notes.main.STATE_FILE", state_file),
			patch("pretty_release_notes.main.GitHubClient", return_value=github),
			patch("pretty_release_notes.main.ReleaseNotesGenerator") as mock_generator_class,
			patch("pretty_release_notes.main.CLI"),
			patch("pretty_release_notes.labeler.WRITE_DELAY", 0),
		):
			mock_generator = mock_generator_class.return_value
			mock_generator.generate.return_value = "# Notes"
			mock_generator.update_on_github.return_value = update_succeeds

			result = runner.invoke(app, ["poll", "--config-path", str(config_file), *(extra_args or [])])

		state = json.loads(state_file.read_text()) if state_file.exists() else {}
		return result, state, mock_generator

	def test_poll_marks_release_processed_after_update(self, tmp_path):
		self._write_config(tmp_path)
		github = FakeGitHub({"v1.0.0": [1]})

		result, state, _ = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		assert state == {"processed": {"owner/repo": ["v1.0.0"]}, "labeled": {}}
		assert github.comments == []
		assert github.generated == []

	def test_poll_retries_release_when_github_rejects_update(self, tmp_path):
		self._write_config(tmp_path, release_label="released")
		github = FakeGitHub({"v1.0.0": [1]})

		result, state, _ = self._run_poll(tmp_path, github, update_succeeds=False)

		assert result.exit_code == 0, result.output
		assert "v1.0.0" not in state["processed"].get("owner/repo", [])
		assert "FAILED owner/repo v1.0.0" in result.output
		# The notes step failed, but labeling is independent
		assert state["labeled"] == {"owner/repo": ["v1.0.0"]}

	def test_poll_labels_and_comments_unlabeled_prs(self, tmp_path):
		self._write_config(tmp_path, release_label="released")
		github = FakeGitHub({"v1.1.0": [1, 2, 3]}, labels={2: {"released"}, 3: {"bug"}})

		result, state, _ = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		assert github.generated == [("v1.1.0", "v0.9.0")]
		assert github.commented_prs() == [1, 3]
		assert github.comments[0][1] == (
			":tada: This PR is included in version 1.1.0 :tada:\n\n"
			"The release is available on [GitHub release](https://github.com/owner/repo/releases/tag/v1.1.0)"
		)
		assert github.labels == {1: {"released"}, 2: {"released"}, 3: {"bug", "released"}}
		assert state == {"processed": {"owner/repo": ["v1.1.0"]}, "labeled": {"owner/repo": ["v1.1.0"]}}

	def test_poll_resumes_labeling_after_rate_limit(self, tmp_path):
		self._write_config(tmp_path, release_label="released")
		github = FakeGitHub({"v1.1.0": [1, 2, 3]})
		github.write_limit = 2  # comment and label PR 1, then fail on the comment for PR 2

		result, state, first_generator = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		assert "FAILED labeling owner/repo v1.1.0" in result.output
		assert github.commented_prs() == [1]
		assert state == {"processed": {"owner/repo": ["v1.1.0"]}, "labeled": {}}
		first_generator.generate.assert_called_once_with("v1.1.0")

		github.write_limit = None
		result, state, second_generator = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		second_generator.generate.assert_not_called()
		assert github.commented_prs() == [1, 2, 3]
		assert github.labels == {1: {"released"}, 2: {"released"}, 3: {"released"}}
		assert state == {"processed": {"owner/repo": ["v1.1.0"]}, "labeled": {"owner/repo": ["v1.1.0"]}}

	def test_poll_stops_labeling_for_the_cycle_after_a_failure(self, tmp_path):
		self._write_config(tmp_path, release_label="released")
		github = FakeGitHub({"v1.1.0": [1], "v1.0.0": [2]})
		github.write_limit = 0  # rate limited from the first write

		result, state, generator = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		# Labeling stops after the first failure, but the notes step continues for all releases
		assert github.generated == [("v1.1.0", "v0.9.0")]
		assert github.writes == 0
		assert state == {"processed": {"owner/repo": ["v1.0.0", "v1.1.0"]}, "labeled": {}}
		assert generator.generate.call_count == 2

	def test_poll_seed_marks_releases_as_labeled(self, tmp_path):
		self._write_config(tmp_path, release_label="released")
		github = FakeGitHub({"v1.1.0": [1], "v1.0.0": [2]})

		result, state, _ = self._run_poll(tmp_path, github, extra_args=["--seed"])

		assert result.exit_code == 0, result.output
		tags = ["v1.1.0", "v1.0.0"]
		assert state == {"processed": {"owner/repo": tags}, "labeled": {"owner/repo": tags}}

		result, state, generator = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		generator.generate.assert_not_called()
		assert github.generated == []
		assert github.comments == []

	def test_poll_migrates_old_state_format(self, tmp_path):
		self._write_config(tmp_path, release_label="released")
		(tmp_path / "processed_releases.json").write_text(json.dumps({"owner/repo": ["v1.0.0"]}))
		github = FakeGitHub({"v1.1.0": [2], "v1.0.0": [1]})

		result, state, generator = self._run_poll(tmp_path, github)

		assert result.exit_code == 0, result.output
		# Releases from the old state were processed before labeling existed: do not comment on them
		generator.generate.assert_called_once_with("v1.1.0")
		assert github.generated == [("v1.1.0", "v0.9.0")]
		assert github.commented_prs() == [2]
		tags = ["v1.1.0", "v1.0.0"]
		assert state == {"processed": {"owner/repo": tags}, "labeled": {"owner/repo": tags}}
