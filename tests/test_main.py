from unittest.mock import patch

from typer.testing import CliRunner

from pretty_release_notes.core.config import DatabaseConfig, GitHubConfig, LLMConfig, ReleaseNotesConfig
from pretty_release_notes.main import app

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
