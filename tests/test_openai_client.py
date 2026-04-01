"""Tests for the any-llm-backed chat client wrapper."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest
from tenacity import stop_after_attempt, wait_none

from pretty_release_notes.openai_client import format_model_name, get_chat_response


def _mock_completion_response(content: str):
	return SimpleNamespace(
		choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
	)


class TestOpenAIClient:
	"""Test the compatibility wrapper around any-llm."""

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_plain_model_defaults_to_openai_provider_for_backward_compatibility(self, mock_acompletion):
		mock_acompletion.return_value = _mock_completion_response("summary")

		result = get_chat_response(
			content="Write a summary",
			model="gpt-4.1",
			api_key="test-key",
		)

		assert result == "summary"
		mock_acompletion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="gpt-4.1",
			provider="openai",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="auto",
		)

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_openai_flex_models_keep_service_tier(self, mock_acompletion):
		mock_acompletion.return_value = _mock_completion_response("summary")

		get_chat_response(
			content="Write a summary",
			model="gpt-5",
			api_key="test-key",
		)

		mock_acompletion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="gpt-5",
			provider="openai",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="flex",
		)

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_reasoning_effort_is_passed_when_configured(self, mock_acompletion):
		mock_acompletion.return_value = _mock_completion_response("summary")

		get_chat_response(
			content="Write a summary",
			model="openai:gpt-5",
			api_key="test-key",
			reasoning_effort="high",
		)

		mock_acompletion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="openai:gpt-5",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="flex",
			reasoning_effort="high",
		)

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_provider_prefixed_model_is_passed_through_to_any_llm(self, mock_acompletion):
		mock_acompletion.return_value = _mock_completion_response("summary")

		result = get_chat_response(
			content="Write a summary",
			model="anthropic:claude-sonnet-4-5",
			api_key="test-key",
		)

		assert result == "summary"
		mock_acompletion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="anthropic:claude-sonnet-4-5",
			api_key="test-key",
		)

	def test_format_model_name_supports_provider_prefixed_models(self):
		assert format_model_name("openai:gpt-4.1") == "OpenAI gpt-4.1"
		assert format_model_name("gpt-4.1") == "OpenAI gpt-4.1"
		assert format_model_name("openrouter:deepseek-r1") == "openrouter:deepseek-r1"

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_prefixed_openai_models_keep_openai_specific_kwargs(self, mock_acompletion):
		mock_acompletion.return_value = _mock_completion_response("summary")

		get_chat_response(
			content="Write a summary",
			model="openai:gpt-5",
			api_key="test-key",
		)

		mock_acompletion.assert_called_once_with(
			messages=[{"role": "user", "content": "Write a summary"}],
			model="openai:gpt-5",
			api_key="test-key",
			client_args={"timeout": 900.0},
			service_tier="flex",
		)

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_worker_thread_drains_background_cleanup_tasks(self, mock_acompletion):
		state = {"cleanup_finished": False}

		async def fake_acompletion(**kwargs):
			async def background_cleanup():
				await asyncio.sleep(0)
				state["cleanup_finished"] = True

			asyncio.create_task(background_cleanup())
			return _mock_completion_response("summary")

		mock_acompletion.side_effect = fake_acompletion

		with ThreadPoolExecutor(max_workers=1) as executor:
			result = executor.submit(
				get_chat_response,
				content="Write a summary",
				model="gpt-5",
				api_key="test-key",
			).result()

		assert result == "summary"
		assert state["cleanup_finished"] is True

	@patch("pretty_release_notes.openai_client.acompletion")
	def test_retries_reraise_last_provider_error(self, mock_acompletion):
		retrying = cast(Any, get_chat_response).retry
		original_stop = retrying.stop
		original_wait = retrying.wait
		mock_acompletion.side_effect = RuntimeError("provider exploded")

		try:
			retrying.stop = stop_after_attempt(1)
			retrying.wait = wait_none()

			with pytest.raises(RuntimeError, match="provider exploded"):
				get_chat_response(
					content="Write a summary",
					model="gpt-5",
					api_key="test-key",
				)
		finally:
			retrying.stop = original_stop
			retrying.wait = original_wait
