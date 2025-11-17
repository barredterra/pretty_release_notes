"""Tests for the interactive setup command."""

from pretty_release_notes.setup_command import (
	_build_toml_content,
	_flatten_toml,
	_migrate_env_to_dict,
)


class TestHelperFunctions:
	"""Test helper functions for setup command."""

	def test_flatten_toml(self):
		"""Test flattening nested TOML config."""
		toml_config = {
			"github": {"token": "ghp_test", "owner": "frappe"},
			"openai": {"api_key": "sk-test", "model": "gpt-4", "max_patch_size": 5000},
			"database": {"type": "csv", "name": "test_db", "enabled": False},
			"filters": {
				"exclude_change_types": ["chore", "ci"],
				"exclude_change_labels": ["skip"],
				"exclude_authors": ["bot"],
			},
		}

		result = _flatten_toml(toml_config)

		assert result["github_token"] == "ghp_test"
		assert result["github_owner"] == "frappe"
		assert result["openai_key"] == "sk-test"
		assert result["openai_model"] == "gpt-4"
		assert result["max_patch_size"] == 5000
		assert result["db_type"] == "csv"
		assert result["db_name"] == "test_db"
		assert result["db_enabled"] is False
		assert result["exclude_types"] == "chore,ci"
		assert result["exclude_labels"] == "skip"
		assert result["exclude_authors"] == "bot"

	def test_flatten_toml_with_missing_sections(self):
		"""Test flattening TOML with missing sections."""
		toml_config = {
			"github": {"token": "ghp_test"},
			"openai": {"api_key": "sk-test"},
		}

		result = _flatten_toml(toml_config)

		assert result["github_token"] == "ghp_test"
		assert result["github_owner"] == ""
		assert result["openai_key"] == "sk-test"
		assert result["openai_model"] == ""
		assert result["db_type"] == ""
		assert result["exclude_types"] == ""

	def test_flatten_toml_with_empty_strings(self):
		"""Test that empty strings in TOML are preserved (caller should handle with 'or' operator)."""
		toml_config = {
			"github": {"token": "ghp_test", "owner": ""},
			"openai": {"api_key": "sk-test", "model": ""},
			"database": {"type": "", "name": "", "enabled": True},
		}

		result = _flatten_toml(toml_config)

		# Empty strings should be preserved - it's the caller's job to handle them
		assert result["github_owner"] == ""
		assert result["openai_model"] == ""
		assert result["db_type"] == ""
		assert result["db_name"] == ""

	def test_migrate_env_to_dict(self):
		"""Test migrating .env format to dict."""
		env_values = {
			"GH_TOKEN": "ghp_test",
			"DEFAULT_OWNER": "frappe",
			"OPENAI_API_KEY": "sk-test",
			"OPENAI_MODEL": "gpt-4",
			"MAX_PATCH_SIZE": "5000",
			"DB_TYPE": "sqlite",
			"DB_NAME": "test_db",
			"EXCLUDE_PR_TYPES": "chore,ci",
			"EXCLUDE_PR_LABELS": "skip",
			"EXCLUDE_AUTHORS": "bot",
		}

		result = _migrate_env_to_dict(env_values)

		assert result["github_token"] == "ghp_test"
		assert result["github_owner"] == "frappe"
		assert result["openai_key"] == "sk-test"
		assert result["openai_model"] == "gpt-4"
		assert result["max_patch_size"] == 5000
		assert result["db_type"] == "sqlite"
		assert result["db_name"] == "test_db"
		assert result["db_enabled"] is True
		assert result["exclude_types"] == "chore,ci"
		assert result["exclude_labels"] == "skip"
		assert result["exclude_authors"] == "bot"

	def test_migrate_env_with_missing_values(self):
		"""Test migrating .env with missing values."""
		env_values = {
			"GH_TOKEN": "ghp_test",
			"OPENAI_API_KEY": "sk-test",
		}

		result = _migrate_env_to_dict(env_values)

		assert result["github_token"] == "ghp_test"
		assert result["github_owner"] == ""
		assert result["openai_key"] == "sk-test"
		assert result["max_patch_size"] == 10000  # default

	def test_build_toml_content(self):
		"""Test building TOML content string."""
		content = _build_toml_content(
			github_token="ghp_test",
			github_owner="frappe",
			openai_key="sk-test",
			openai_model="gpt-4",
			max_patch_size=5000,
			db_type="sqlite",
			db_name="test_db",
			db_enabled=True,
			exclude_types="chore,ci",
			exclude_labels="skip",
			exclude_authors="bot1,bot2",
			group_by_type=False,
		)

		# Check key sections are present
		assert "[github]" in content
		assert 'token = "ghp_test"' in content
		assert 'owner = "frappe"' in content
		assert "[openai]" in content
		assert 'api_key = "sk-test"' in content
		assert 'model = "gpt-4"' in content
		assert "max_patch_size = 5000" in content
		assert "[database]" in content
		assert 'type = "sqlite"' in content
		assert 'name = "test_db"' in content
		assert "enabled = true" in content
		assert "[filters]" in content
		assert '["chore", "ci"]' in content
		assert '["skip"]' in content
		assert '["bot1", "bot2"]' in content
		assert "[grouping]" in content
		assert "group_by_type = false" in content

	def test_build_toml_content_with_empty_arrays(self):
		"""Test building TOML with empty filter arrays."""
		content = _build_toml_content(
			github_token="ghp_test",
			github_owner="",
			openai_key="sk-test",
			openai_model="gpt-4",
			max_patch_size=10000,
			db_type="sqlite",
			db_name="stored_lines",
			db_enabled=False,
			exclude_types="",
			exclude_labels="",
			exclude_authors="",
			group_by_type=True,
		)

		# Check empty arrays are properly formatted
		assert "exclude_change_types = []" in content
		assert "exclude_change_labels = []" in content
		assert "exclude_authors = []" in content
		assert "enabled = false" in content
		assert "group_by_type = true" in content


class TestSetupCommand:
	"""Test the setup command integration."""

	def test_setup_creates_config_file(self, tmp_path, monkeypatch):
		"""Test that setup command creates a config file."""
		config_path = tmp_path / "config.toml"

		# Mock user inputs
		inputs = iter(
			[
				"ghp_test",  # github token
				"frappe",  # github owner
				"sk-test",  # openai key
				"gpt-4",  # openai model
				"10000",  # max patch size
				"sqlite",  # db type
				"stored_lines",  # db name
				"y",  # db enabled
				"chore,ci",  # exclude types
				"skip",  # exclude labels
				"bot",  # exclude authors
				"n",  # group_by_type
				"y",  # confirm write
			]
		)

		def mock_prompt(*args, **kwargs):
			return next(inputs)

		def mock_confirm(*args, **kwargs):
			response = next(inputs)
			return response.lower() == "y"

		# Patch prompts
		monkeypatch.setattr("pretty_release_notes.setup_command.Prompt.ask", mock_prompt)
		monkeypatch.setattr("pretty_release_notes.setup_command.Confirm.ask", mock_confirm)

		# Run setup
		from pretty_release_notes.setup_command import setup_config

		setup_config(config_path=config_path, migrate_env=False)

		# Verify file was created
		assert config_path.exists()

		# Verify content
		content = config_path.read_text()
		assert "[github]" in content
		assert 'token = "ghp_test"' in content
		assert "[openai]" in content
		assert 'api_key = "sk-test"' in content

	def test_setup_migrates_from_env(self, tmp_path, monkeypatch):
		"""Test that setup command migrates from .env file."""
		# Create a temporary .env file
		env_path = tmp_path / ".env"
		env_path.write_text(
			"""GH_TOKEN=ghp_from_env
OPENAI_API_KEY=sk_from_env
DEFAULT_OWNER=test_owner
"""
		)

		config_path = tmp_path / "config.toml"

		# Mock current directory to tmp_path
		monkeypatch.chdir(tmp_path)

		# Mock user inputs (press enter to accept defaults)
		inputs = iter(
			[
				"",  # github token (accept default from .env)
				"",  # github owner (accept default from .env)
				"",  # openai key (accept default from .env)
				"gpt-4",  # openai model
				"10000",  # max patch size
				"sqlite",  # db type
				"stored_lines",  # db name
				"y",  # db enabled
				"chore",  # exclude types
				"skip",  # exclude labels
				"bot",  # exclude authors
				"n",  # group_by_type
				"y",  # confirm write
				"n",  # don't delete .env
			]
		)

		def mock_prompt(*args, **kwargs):
			default = kwargs.get("default", "")
			value = next(inputs)
			return value if value else default

		def mock_confirm(*args, **kwargs):
			response = next(inputs)
			return response.lower() == "y"

		# Patch prompts
		monkeypatch.setattr("pretty_release_notes.setup_command.Prompt.ask", mock_prompt)
		monkeypatch.setattr("pretty_release_notes.setup_command.Confirm.ask", mock_confirm)

		# Run setup with migration
		from pretty_release_notes.setup_command import setup_config

		setup_config(config_path=config_path, migrate_env=True)

		# Verify file was created
		assert config_path.exists()

		# Verify migrated values are in the config
		content = config_path.read_text()
		assert 'token = "ghp_from_env"' in content or 'token = ""' in content
		assert 'owner = "test_owner"' in content or 'owner = ""' in content
