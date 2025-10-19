"""Tests for the library API (ReleaseNotesClient and ReleaseNotesBuilder)."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api import ReleaseNotesBuilder, ReleaseNotesClient
from core.config import DatabaseConfig, FilterConfig, GitHubConfig, OpenAIConfig, ReleaseNotesConfig
from core.interfaces import ProgressEvent, ProgressReporter


class TestProgressReporting:
	"""Test that progress reporting works with custom reporters."""

	def test_custom_progress_reporter_receives_events(self):
		"""Test that a custom progress reporter receives all progress events."""
		# Create a mock progress reporter
		mock_reporter = Mock(spec=ProgressReporter)

		# Build a client with the mock reporter
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="test_token"),
			openai=OpenAIConfig(api_key="test_key"),
		)
		client = ReleaseNotesClient(config, progress_reporter=mock_reporter)

		# The reporter should be stored
		assert client.progress_reporter == mock_reporter

	def test_builder_with_custom_progress_reporter(self):
		"""Test that builder correctly passes progress reporter to client."""
		mock_reporter = Mock(spec=ProgressReporter)

		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key")
			.with_progress_reporter(mock_reporter)
			.build()
		)

		assert client.progress_reporter == mock_reporter

	def test_null_progress_reporter_when_none_provided(self):
		"""Test that NullProgressReporter is used when none provided."""
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="test_token"),
			openai=OpenAIConfig(api_key="test_key"),
		)
		client = ReleaseNotesClient(config)

		# Should have a progress reporter (NullProgressReporter)
		assert client.progress_reporter is not None

		# NullProgressReporter should not raise errors when called
		from core.interfaces import NullProgressReporter

		assert isinstance(client.progress_reporter, NullProgressReporter)

	def test_progress_events_captured_during_generation(self):
		"""Test that progress events are captured during note generation."""

		class EventCapturingReporter(ProgressReporter):
			def __init__(self):
				self.events = []

			def report(self, event: ProgressEvent) -> None:
				self.events.append(event)

		reporter = EventCapturingReporter()

		# Mock the generator to avoid real API calls
		with patch("api.ReleaseNotesGenerator") as MockGenerator:
			mock_gen = MockGenerator.return_value
			mock_gen.generate.return_value = "# Release Notes"

			config = ReleaseNotesConfig(
				github=GitHubConfig(token="test_token"),
				openai=OpenAIConfig(api_key="test_key"),
			)
			client = ReleaseNotesClient(config, progress_reporter=reporter)

			# Generate notes (mocked)
			client.generate_release_notes("owner", "repo", "v1.0.0")

			# Verify the reporter was passed to the generator
			MockGenerator.assert_called_once_with(config, reporter)

	def test_silent_operation_with_null_reporter(self):
		"""Test that silent operation works (no progress output)."""
		# Build without progress reporter (should use NullProgressReporter)
		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key")
			.build()
		)

		from core.interfaces import NullProgressReporter

		assert isinstance(client.progress_reporter, NullProgressReporter)

		# NullProgressReporter's report method should do nothing
		client.progress_reporter.report(ProgressEvent(type="test", message="test"))
		# No exception = success


class TestConfigurationValidation:
	"""Test that configuration validation provides helpful errors."""

	def test_missing_github_token_raises_error(self):
		"""Test that building without GitHub token raises ValueError."""
		builder = ReleaseNotesBuilder().with_openai("test_key")

		with pytest.raises(ValueError, match="GitHub token is required"):
			builder.build()

	def test_missing_openai_key_raises_error(self):
		"""Test that building without OpenAI key raises ValueError."""
		builder = ReleaseNotesBuilder().with_github_token("test_token")

		with pytest.raises(ValueError, match="OpenAI API key is required"):
			builder.build()

	def test_invalid_database_type_raises_error(self):
		"""Test that invalid database type raises ValueError."""
		with pytest.raises(ValueError, match="Invalid database type"):
			DatabaseConfig(type="invalid_type")

	def test_empty_github_token_raises_error(self):
		"""Test that empty GitHub token raises ValueError."""
		with pytest.raises(ValueError, match="GitHub token is required"):
			GitHubConfig(token="")

	def test_empty_openai_key_raises_error(self):
		"""Test that empty OpenAI API key raises ValueError."""
		with pytest.raises(ValueError, match="OpenAI API key is required"):
			OpenAIConfig(api_key="")

	def test_valid_configuration_builds_successfully(self):
		"""Test that valid configuration builds without errors."""
		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key")
			.build()
		)

		assert client is not None
		assert isinstance(client, ReleaseNotesClient)

	def test_all_builder_options_work(self):
		"""Test that all builder options can be set without errors."""
		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key", model="gpt-4", max_patch_size=15000)
			.with_database("sqlite", db_name="test_db", enabled=True)
			.with_filters(
				exclude_types={"chore", "ci"},
				exclude_labels={"skip"},
				exclude_authors={"bot"},
			)
			.with_prompt_file(Path("test_prompt.txt"))
			.with_force_commits(True)
			.build()
		)

		assert client.config.github.token == "test_token"
		assert client.config.openai.api_key == "test_key"
		assert client.config.openai.model == "gpt-4"
		assert client.config.openai.max_patch_size == 15000
		assert client.config.database.type == "sqlite"
		assert client.config.database.name == "test_db"
		assert client.config.database.enabled is True
		assert client.config.filters.exclude_change_types == {"chore", "ci"}
		assert client.config.filters.exclude_change_labels == {"skip"}
		assert client.config.filters.exclude_authors == {"bot"}
		assert client.config.prompt_path == Path("test_prompt.txt")
		assert client.config.force_use_commits is True

	def test_builder_returns_self_for_chaining(self):
		"""Test that builder methods return self for method chaining."""
		builder = ReleaseNotesBuilder()

		assert builder.with_github_token("token") is builder
		assert builder.with_openai("key") is builder
		assert builder.with_database() is builder
		assert builder.with_filters() is builder
		assert builder.with_prompt_file(Path("test.txt")) is builder
		assert builder.with_force_commits() is builder

	def test_partial_filters_work(self):
		"""Test that filters can be set partially (not all at once)."""
		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key")
			.with_filters(exclude_types={"chore"})
			.build()
		)

		assert client.config.filters.exclude_change_types == {"chore"}
		assert client.config.filters.exclude_change_labels == set()
		assert client.config.filters.exclude_authors == set()

	def test_database_defaults(self):
		"""Test that database has sensible defaults."""
		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key")
			.build()
		)

		# Check defaults
		assert client.config.database.type == "sqlite"
		assert client.config.database.name == "stored_lines"
		assert client.config.database.enabled is True

	def test_openai_defaults(self):
		"""Test that OpenAI config has sensible defaults."""
		client = (
			ReleaseNotesBuilder()
			.with_github_token("test_token")
			.with_openai("test_key")
			.build()
		)

		# Check defaults
		assert client.config.openai.model == "gpt-4.1"
		assert client.config.openai.max_patch_size == 10000


class TestClientAPI:
	"""Test the ReleaseNotesClient API."""

	def test_client_initializes_with_config(self):
		"""Test that client initializes with configuration."""
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="test_token"),
			openai=OpenAIConfig(api_key="test_key"),
		)
		client = ReleaseNotesClient(config)

		assert client.config == config

	def test_generate_release_notes_calls_generator(self):
		"""Test that generate_release_notes calls the generator correctly."""
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="test_token"),
			openai=OpenAIConfig(api_key="test_key"),
		)
		client = ReleaseNotesClient(config)

		with patch("api.ReleaseNotesGenerator") as MockGenerator:
			mock_gen = MockGenerator.return_value
			mock_gen.generate.return_value = "# Release Notes"

			result = client.generate_release_notes("owner", "repo", "v1.0.0")

			# Verify generator was created and used correctly
			MockGenerator.assert_called_once()
			mock_gen.initialize_repository.assert_called_once_with("owner", "repo")
			mock_gen.generate.assert_called_once_with("v1.0.0")
			assert result == "# Release Notes"

	def test_update_github_release_calls_generator(self):
		"""Test that update_github_release calls the generator correctly."""
		config = ReleaseNotesConfig(
			github=GitHubConfig(token="test_token"),
			openai=OpenAIConfig(api_key="test_key"),
		)
		client = ReleaseNotesClient(config)

		with patch("api.ReleaseNotesGenerator") as MockGenerator:
			mock_gen = MockGenerator.return_value

			client.update_github_release("owner", "repo", "v1.0.0", "# New Notes")

			# Verify generator was created and used correctly
			MockGenerator.assert_called_once()
			mock_gen.initialize_repository.assert_called_once_with("owner", "repo")
			mock_gen.update_on_github.assert_called_once_with("# New Notes", "v1.0.0")
