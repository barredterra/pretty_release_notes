"""Unit tests for core configuration and interfaces."""

from pathlib import Path

import pytest

from pretty_release_notes.core.config import (
	DatabaseConfig,
	FilterConfig,
	GitHubConfig,
	GroupingConfig,
	OpenAIConfig,
	ReleaseNotesConfig,
)
from pretty_release_notes.core.config_loader import DictConfigLoader, TomlConfigLoader
from pretty_release_notes.core.interfaces import (
	CompositeProgressReporter,
	NullProgressReporter,
	ProgressEvent,
	ProgressReporter,
)


class TestProgressEvent:
	"""Test ProgressEvent dataclass."""

	def test_create_basic_event(self):
		event = ProgressEvent(type="info", message="Test message")
		assert event.type == "info"
		assert event.message == "Test message"
		assert event.metadata is None

	def test_create_event_with_metadata(self):
		metadata = {"key": "value"}
		event = ProgressEvent(type="success", message="Done", metadata=metadata)
		assert event.type == "success"
		assert event.message == "Done"
		assert event.metadata == metadata


class TestProgressReporter:
	"""Test ProgressReporter implementations."""

	def test_null_reporter_does_nothing(self):
		reporter = NullProgressReporter()
		event = ProgressEvent(type="info", message="Test")
		# Should not raise any exception
		reporter.report(event)

	def test_composite_reporter_calls_all(self):
		"""Test that composite reporter calls all sub-reporters."""

		class MockReporter(ProgressReporter):
			def __init__(self):
				self.events = []

			def report(self, event: ProgressEvent) -> None:
				self.events.append(event)

		reporter1 = MockReporter()
		reporter2 = MockReporter()
		composite = CompositeProgressReporter([reporter1, reporter2])

		event = ProgressEvent(type="info", message="Test")
		composite.report(event)

		assert len(reporter1.events) == 1
		assert len(reporter2.events) == 1
		assert reporter1.events[0] == event
		assert reporter2.events[0] == event


class TestGitHubConfig:
	"""Test GitHubConfig validation."""

	def test_valid_config(self):
		config = GitHubConfig(token="test_token")
		assert config.token == "test_token"
		assert config.owner is None

	def test_valid_config_with_owner(self):
		config = GitHubConfig(token="test_token", owner="test_owner")
		assert config.token == "test_token"
		assert config.owner == "test_owner"

	def test_empty_token_raises_error(self):
		with pytest.raises(ValueError, match="GitHub token is required"):
			GitHubConfig(token="")


class TestOpenAIConfig:
	"""Test OpenAIConfig validation."""

	def test_valid_config_with_defaults(self):
		config = OpenAIConfig(api_key="test_key")
		assert config.api_key == "test_key"
		assert config.model == "gpt-4.1"
		assert config.max_patch_size == 10000

	def test_valid_config_with_custom_values(self):
		config = OpenAIConfig(api_key="test_key", model="gpt-4", max_patch_size=5000)
		assert config.api_key == "test_key"
		assert config.model == "gpt-4"
		assert config.max_patch_size == 5000

	def test_empty_api_key_raises_error(self):
		with pytest.raises(ValueError, match="OpenAI API key is required"):
			OpenAIConfig(api_key="")


class TestDatabaseConfig:
	"""Test DatabaseConfig validation."""

	def test_valid_config_with_defaults(self):
		config = DatabaseConfig()
		assert config.type == "sqlite"
		assert config.name == "stored_lines"
		assert config.enabled is True

	def test_valid_config_with_csv(self):
		config = DatabaseConfig(type="csv", name="custom_cache", enabled=False)
		assert config.type == "csv"
		assert config.name == "custom_cache"
		assert config.enabled is False

	def test_invalid_type_raises_error(self):
		with pytest.raises(ValueError, match="Invalid database type: redis"):
			DatabaseConfig(type="redis")


class TestFilterConfig:
	"""Test FilterConfig."""

	def test_default_empty_sets(self):
		config = FilterConfig()
		assert config.exclude_change_types == set()
		assert config.exclude_change_labels == set()
		assert config.exclude_authors == set()

	def test_with_custom_filters(self):
		config = FilterConfig(
			exclude_change_types={"chore", "refactor"},
			exclude_change_labels={"skip"},
			exclude_authors={"bot"},
		)
		assert config.exclude_change_types == {"chore", "refactor"}
		assert config.exclude_change_labels == {"skip"}
		assert config.exclude_authors == {"bot"}


class TestGroupingConfig:
	"""Test GroupingConfig."""

	def test_default_config(self):
		"""Test default grouping configuration."""
		config = GroupingConfig()
		assert config.group_by_type is False
		assert config.other_heading == "Other Changes"
		assert config.get_heading("feat") == "Features"
		assert config.get_heading("fix") == "Bug Fixes"
		assert config.get_heading(None) == "Other Changes"
		assert config.get_heading("unknown") == "Other Changes"

	def test_custom_headings(self):
		"""Test custom type headings."""
		config = GroupingConfig(
			group_by_type=True,
			type_headings={"feat": "New Features", "fix": "Fixes"},
			other_heading="Miscellaneous",
		)
		assert config.get_heading("feat") == "New Features"
		assert config.get_heading("fix") == "Fixes"
		assert config.get_heading("unknown") == "Miscellaneous"

	def test_release_notes_config_with_grouping(self):
		"""Test ReleaseNotesConfig includes GroupingConfig."""
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="token"),
			openai=OpenAIConfig(api_key="key"),
			grouping=GroupingConfig(group_by_type=True),
		)
		assert config.grouping.group_by_type is True


class TestReleaseNotesConfig:
	"""Test ReleaseNotesConfig."""

	def test_minimal_config(self):
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="gh_token"),
			openai=OpenAIConfig(api_key="openai_key"),
		)
		assert config.github.token == "gh_token"
		assert config.openai.api_key == "openai_key"
		assert config.database.type == "sqlite"
		assert config.filters.exclude_change_types == set()
		# Check that prompt_path is set to the package's prompt.txt
		assert config.prompt_path.name == "prompt.txt"
		assert config.prompt_path.exists()
		assert config.force_use_commits is False

	def test_full_config(self):
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="gh_token", owner="owner"),
			openai=OpenAIConfig(api_key="openai_key", model="gpt-4"),
			database=DatabaseConfig(type="csv", enabled=False),
			filters=FilterConfig(exclude_change_types={"chore"}),
			prompt_path=Path("custom_prompt.txt"),
			force_use_commits=True,
		)
		assert config.github.owner == "owner"
		assert config.openai.model == "gpt-4"
		assert config.database.type == "csv"
		assert config.database.enabled is False
		assert config.filters.exclude_change_types == {"chore"}
		assert config.prompt_path == Path("custom_prompt.txt")
		assert config.force_use_commits is True


class TestDictConfigLoader:
	"""Test DictConfigLoader."""

	def test_load_minimal_config(self):
		config_dict = {"github_token": "gh_token", "openai_api_key": "openai_key"}
		loader = DictConfigLoader(config_dict)
		config = loader.load()

		assert config.github.token == "gh_token"
		assert config.openai.api_key == "openai_key"
		assert config.database.type == "sqlite"

	def test_load_full_config(self):
		config_dict = {
			"github_token": "gh_token",
			"github_owner": "test_owner",
			"openai_api_key": "openai_key",
			"openai_model": "gpt-4",
			"max_patch_size": 5000,
			"db_type": "csv",
			"db_name": "custom_db",
			"use_db": False,
			"exclude_types": ["chore", "refactor"],
			"exclude_labels": ["skip"],
			"exclude_authors": ["bot"],
			"prompt_path": "custom.txt",
			"force_use_commits": True,
		}
		loader = DictConfigLoader(config_dict)
		config = loader.load()

		assert config.github.token == "gh_token"
		assert config.github.owner == "test_owner"
		assert config.openai.api_key == "openai_key"
		assert config.openai.model == "gpt-4"
		assert config.openai.max_patch_size == 5000
		assert config.database.type == "csv"
		assert config.database.name == "custom_db"
		assert config.database.enabled is False
		assert config.filters.exclude_change_types == {"chore", "refactor"}
		assert config.filters.exclude_change_labels == {"skip"}
		assert config.filters.exclude_authors == {"bot"}
		assert config.prompt_path == Path("custom.txt")
		assert config.force_use_commits is True

	def test_missing_required_raises_error(self):
		config_dict = {"openai_api_key": "openai_key"}
		loader = DictConfigLoader(config_dict)
		with pytest.raises(KeyError):
			loader.load()


class TestTomlConfigLoader:
	"""Test TomlConfigLoader."""

	def test_load_minimal_config(self, tmp_path):
		config_file = tmp_path / "config.toml"
		config_file.write_text(
			"""
[github]
token = "gh_token"

[openai]
api_key = "openai_key"
"""
		)

		loader = TomlConfigLoader(config_file)
		config = loader.load()

		assert config.github.token == "gh_token"
		assert config.openai.api_key == "openai_key"
		assert config.database.type == "sqlite"

	def test_load_full_config(self, tmp_path):
		config_file = tmp_path / "config.toml"
		config_file.write_text(
			"""prompt_path = "custom.txt"
force_use_commits = true

[github]
token = "gh_token"
owner = "test_owner"

[openai]
api_key = "openai_key"
model = "gpt-4"
max_patch_size = 5000

[database]
type = "csv"
name = "custom_db"
enabled = false

[filters]
exclude_change_types = ["chore", "refactor"]
exclude_change_labels = ["skip"]
exclude_authors = ["bot"]
"""
		)

		loader = TomlConfigLoader(config_file)
		config = loader.load()

		assert config.github.token == "gh_token"
		assert config.github.owner == "test_owner"
		assert config.openai.api_key == "openai_key"
		assert config.openai.model == "gpt-4"
		assert config.openai.max_patch_size == 5000
		assert config.database.type == "csv"
		assert config.database.name == "custom_db"
		assert config.database.enabled is False
		assert config.filters.exclude_change_types == {"chore", "refactor"}
		assert config.filters.exclude_change_labels == {"skip"}
		assert config.filters.exclude_authors == {"bot"}
		assert config.prompt_path == Path("custom.txt")
		assert config.force_use_commits is True

	def test_missing_file_raises_error(self, tmp_path):
		config_file = tmp_path / "nonexistent.toml"
		loader = TomlConfigLoader(config_file)
		with pytest.raises(FileNotFoundError, match="Config file not found"):
			loader.load()

	def test_missing_required_github_token_raises_error(self, tmp_path):
		config_file = tmp_path / "config.toml"
		config_file.write_text(
			"""
[github]

[openai]
api_key = "openai_key"
"""
		)

		loader = TomlConfigLoader(config_file)
		with pytest.raises(ValueError, match="github.token is required"):
			loader.load()

	def test_missing_required_openai_key_raises_error(self, tmp_path):
		config_file = tmp_path / "config.toml"
		config_file.write_text(
			"""
[github]
token = "gh_token"

[openai]
"""
		)

		loader = TomlConfigLoader(config_file)
		with pytest.raises(ValueError, match="openai.api_key is required"):
			loader.load()

	def test_default_config_path(self):
		loader = TomlConfigLoader()
		expected_path = Path.home() / ".pretty-release-notes" / "config.toml"
		assert loader.config_path == expected_path
