from typing import Any, cast
from unittest.mock import patch

from pretty_release_notes.core.config import DatabaseConfig, GitHubConfig, LLMConfig, ReleaseNotesConfig
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
