import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal, TypeVar, cast

from any_llm import AnyLLM, acompletion
from tenacity import (
	retry,
	stop_after_attempt,
	wait_random_exponential,
)

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "openai:o3"
ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]
SUPPORTED_REASONING_EFFORTS: tuple[ReasoningEffort, ...] = ("none", "low", "medium", "high", "xhigh")
T = TypeVar("T")
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


def _get_pending_tasks() -> list[asyncio.Task[Any]]:
	current_task = asyncio.current_task()
	return [task for task in asyncio.all_tasks() if task is not current_task and not task.done()]


async def _run_with_cleanup(coro: Coroutine[Any, Any, T]) -> T:
	try:
		result = await coro
		# Give libraries a tick to schedule async cleanup before we tear the loop down.
		await asyncio.sleep(0)
		pending_tasks = _get_pending_tasks()
		if pending_tasks:
			await asyncio.gather(*pending_tasks, return_exceptions=True)
	except Exception:
		pending_tasks = _get_pending_tasks()
		for task in pending_tasks:
			task.cancel()
		if pending_tasks:
			await asyncio.gather(*pending_tasks, return_exceptions=True)
		raise
	return result


def _run_coro_in_new_loop(coro_factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
	loop = asyncio.new_event_loop()
	try:
		asyncio.set_event_loop(loop)
		return loop.run_until_complete(_run_with_cleanup(coro_factory()))
	finally:
		try:
			pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
			for task in pending_tasks:
				task.cancel()
			if pending_tasks:
				loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
			loop.run_until_complete(loop.shutdown_asyncgens())
			loop.run_until_complete(loop.shutdown_default_executor())
		finally:
			asyncio.set_event_loop(None)
			loop.close()


def _run_async_in_sync(coro_factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
	try:
		asyncio.get_running_loop()
	except RuntimeError:
		return _run_coro_in_new_loop(coro_factory)

	with ThreadPoolExecutor(max_workers=1) as executor:
		return executor.submit(_run_coro_in_new_loop, coro_factory).result()


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6), reraise=True)
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

	chat_completion: Any = _run_async_in_sync(lambda: acompletion(**completion_kwargs))

	response_content: str | None = chat_completion.choices[0].message.content
	if response_content is None:
		raise ValueError("LLM API returned empty content")
	# At this point, mypy knows response_content is str (not None)
	return str(response_content)
