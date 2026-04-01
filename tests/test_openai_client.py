"""Tests for the any-llm-backed chat client wrapper."""

from types import SimpleNamespace
from unittest.mock import patch

from pretty_release_notes.openai_client import format_model_name, get_chat_response


def _mock_completion_response(content: str):
	return SimpleNamespace(
		choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
	)


class TestOpenAIClient:
	"""Test the compatibility wrapper around any-llm."""

	@patch("pretty_release_notes.openai_client.completion")
	def test_plain_model_defaults_to_openai_provider_for_backward_compatibility(self, mock_completion):
		mock_completion.return_value = _mock_completion_response("summary")

		result = get_chat_response(
			content="Write a summary",
			model="gpt-4.1",
			api_key="test-key",
		)

		assert result == "summary"
		mock_completion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="gpt-4.1",
			provider="openai",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="auto",
		)

	@patch("pretty_release_notes.openai_client.completion")
	def test_openai_flex_models_keep_service_tier(self, mock_completion):
		mock_completion.return_value = _mock_completion_response("summary")

		get_chat_response(
			content="Write a summary",
			model="gpt-5",
			api_key="test-key",
		)

		mock_completion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="gpt-5",
			provider="openai",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="flex",
		)

	@patch("pretty_release_notes.openai_client.completion")
	def test_reasoning_effort_is_passed_when_configured(self, mock_completion):
		mock_completion.return_value = _mock_completion_response("summary")

		get_chat_response(
			content="Write a summary",
			model="openai:gpt-5",
			api_key="test-key",
			reasoning_effort="high",
		)

		mock_completion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="openai:gpt-5",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="flex",
			reasoning_effort="high",
		)

	@patch("pretty_release_notes.openai_client.completion")
	def test_provider_prefixed_model_is_passed_through_to_any_llm(self, mock_completion):
		mock_completion.return_value = _mock_completion_response("summary")

		result = get_chat_response(
			content="Write a summary",
			model="anthropic:claude-sonnet-4-5",
			api_key="test-key",
		)

		assert result == "summary"
		mock_completion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="anthropic:claude-sonnet-4-5",
			api_key="test-key",
		)

	def test_format_model_name_supports_provider_prefixed_models(self):
		assert format_model_name("openai:gpt-4.1") == "OpenAI gpt-4.1"
		assert format_model_name("gpt-4.1") == "OpenAI gpt-4.1"
		assert format_model_name("openrouter:deepseek-r1") == "openrouter:deepseek-r1"

	@patch("pretty_release_notes.openai_client.completion")
	def test_prefixed_openai_models_keep_openai_specific_kwargs(self, mock_completion):
		mock_completion.return_value = _mock_completion_response("summary")

		get_chat_response(
			content="Write a summary",
			model="openai:gpt-5",
			api_key="test-key",
		)

		mock_completion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="openai:gpt-5",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="flex",
		)
