from typing import Any, Literal, cast

from any_llm import AnyLLM, completion
from tenacity import (
	retry,
	stop_after_attempt,
	wait_random_exponential,
)

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "openai:o3"
ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]
SUPPORTED_REASONING_EFFORTS: tuple[ReasoningEffort, ...] = ("none", "low", "medium", "high", "xhigh")
OPENAI_MODELS_WITH_FLEX = {
	"o3",
	"o4-mini",
	"gpt-5-nano",
	"gpt-5-mini",
	"gpt-5",
	"gpt-5.1",
	"gpt-5.2",
	"gpt-5.4-pro",
	"gpt-5.4",
}


def normalize_reasoning_effort(reasoning_effort: str | None) -> ReasoningEffort | None:
	if reasoning_effort is None:
		return None

	normalized_reasoning_effort = reasoning_effort.strip().lower()
	if not normalized_reasoning_effort:
		return None

	if normalized_reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
		supported_values = ", ".join(SUPPORTED_REASONING_EFFORTS)
		raise ValueError(f"Invalid reasoning effort: {reasoning_effort}. Supported values: {supported_values}")

	return cast(ReasoningEffort, normalized_reasoning_effort)


def _get_model_info(model: str) -> tuple[str, str, bool]:
	model = model.strip()
	try:
		provider, provider_model = AnyLLM.split_model_provider(model)
	except ValueError:
		if ":" in model or "/" in model:
			raise
		return DEFAULT_PROVIDER, model, False
	return provider.value, provider_model, True


def _get_provider_kwargs(provider: str, model: str) -> dict[str, object]:
	if provider != DEFAULT_PROVIDER:
		return {}
	return {
		"client_args": {"timeout": 900.0},
		"service_tier": "flex" if model in OPENAI_MODELS_WITH_FLEX else "auto",
	}


def format_model_name(model: str) -> str:
	"""Format model information for user-facing output."""
	provider, provider_model, _ = _get_model_info(model)
	if provider == DEFAULT_PROVIDER:
		return f"OpenAI {provider_model}"
	return f"{provider}:{provider_model}"


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def get_chat_response(
	content: str,
	model: str,
	api_key: str,
	reasoning_effort: ReasoningEffort | None = None,
) -> str:
	"""Get a chat response through any-llm.

	Raises:
		Exception: If the provider API call fails after all retry attempts
		ValueError: If the provider API returns empty content
	"""
	provider, provider_model, is_provider_qualified = _get_model_info(model)
	normalized_reasoning_effort = normalize_reasoning_effort(reasoning_effort)
	completion_kwargs: dict[str, Any] = {
		"messages": [
			{
				"role": "user",
				"content": content,
			}
		],
		"model": model.strip() if is_provider_qualified else provider_model,
		"api_key": api_key,
		**_get_provider_kwargs(provider, provider_model),
	}

	if not is_provider_qualified:
		completion_kwargs["provider"] = DEFAULT_PROVIDER

	if normalized_reasoning_effort is not None:
		completion_kwargs["reasoning_effort"] = normalized_reasoning_effort

	chat_completion: Any = completion(**completion_kwargs)

	response_content: str | None = chat_completion.choices[0].message.content
	if response_content is None:
		raise ValueError("LLM API returned empty content")
	# At this point, mypy knows response_content is str (not None)
	return str(response_content)
