from typing import Any, cast
from unittest.mock import patch

from tenacity import Future, RetryError

from pretty_release_notes.core.config import DatabaseConfig, GitHubConfig, LLMConfig, ReleaseNotesConfig
from pretty_release_notes.core.interfaces import ProgressEvent, ProgressReporter
from pretty_release_notes.generator import ReleaseNotesGenerator
from pretty_release_notes.models.release_notes_line import ReleaseNotesLine
from pretty_release_notes.models.repository import Repository


class FakeChange:
	html_url = "https://github.com/test/repo/pull/1"
	labels = None
	conventional_type = None

	def get_prompt(self, prompt_template: str, max_patch_size: int) -> str:
		assert prompt_template == "prompt template"
		assert max_patch_size == 10000
		return "generated prompt"

	def get_summary_key(self) -> str:
		return "fake-change"

	def __str__(self) -> str:
		return "Fake Change"


class FakeFailingPullRequest(FakeChange):
	id = 123
	title = "fix: improve auth errors"
	body = "sensitive PR body that should stay out of error messages"

	def __str__(self) -> str:
		return f"PR Title: {self.title}\n\nPR Body: {self.body}"


class CollectingProgressReporter(ProgressReporter):
	def __init__(self):
		self.events: list[ProgressEvent] = []

	def report(self, event: ProgressEvent) -> None:
		self.events.append(event)


def test_generator_passes_reasoning_effort_to_chat_client(tmp_path):
	prompt_path = tmp_path / "prompt.txt"
	prompt_path.write_text("prompt template")

	config = ReleaseNotesConfig(
		github=GitHubConfig(token="gh-token"),
		llm=LLMConfig(api_key="llm-key", reasoning_effort="xhigh"),
		database=DatabaseConfig(enabled=False),
		prompt_path=prompt_path,
	)
	generator = ReleaseNotesGenerator(config)
	generator.repository = Repository(
		owner="test",
		name="repo",
		url="https://api.github.com/repos/test/repo",
		html_url="https://github.com/test/repo",
	)

	line = ReleaseNotesLine(original_line="", change=cast(Any, FakeChange()))

	with patch("pretty_release_notes.generator.get_chat_response", return_value="summary") as mock_get_chat_response:
		generator._process_line(line, "prompt template")

	mock_get_chat_response.assert_called_once_with(
		content="generated prompt",
		model="openai:o3",
		api_key="llm-key",
		reasoning_effort="xhigh",
	)
	assert line.sentence == "summary"


def test_generator_surfaces_underlying_error_without_pr_body(tmp_path):
	prompt_path = tmp_path / "prompt.txt"
	prompt_path.write_text("prompt template")
	progress_reporter = CollectingProgressReporter()

	config = ReleaseNotesConfig(
		github=GitHubConfig(token="gh-token"),
		llm=LLMConfig(api_key="llm-key"),
		database=DatabaseConfig(enabled=False),
		prompt_path=prompt_path,
	)
	generator = ReleaseNotesGenerator(config, progress_reporter)
	generator.repository = Repository(
		owner="test",
		name="repo",
		url="https://api.github.com/repos/test/repo",
		html_url="https://github.com/test/repo",
	)

	line = ReleaseNotesLine(original_line="", change=cast(Any, FakeFailingPullRequest()))
	last_attempt: Future = Future(1)
	last_attempt.set_exception(RuntimeError("quota exhausted"))

	with patch("pretty_release_notes.generator.get_chat_response", side_effect=RetryError(last_attempt)):
		generator._process_line(line, "prompt template")

	assert line.sentence is None
	assert len(progress_reporter.events) == 1
	error_message = progress_reporter.events[0].message
	assert "RetryError" not in error_message
	assert "RuntimeError: quota exhausted" in error_message
	assert "PR #123: fix: improve auth errors" in error_message
	assert "PR Body" not in error_message
	assert "sensitive PR body" not in error_message
