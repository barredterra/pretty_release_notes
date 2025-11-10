from openai import OpenAI
from tenacity import (
	retry,
	stop_after_attempt,
	wait_random_exponential,
)


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def get_chat_response(
	content: str,
	model: str,
	api_key: str,
) -> str:
	"""Get a chat response from OpenAI.

	Raises:
		Exception: If OpenAI API call fails after all retry attempts
		ValueError: If OpenAI API returns empty content
	"""
	client = OpenAI(api_key=api_key, timeout=900.0)

	chat_completion = client.chat.completions.create(
		messages=[
			{
				"role": "user",
				"content": content,
			}
		],
		model=model,
		service_tier="flex" if model in {"o3", "o4-mini"} else "auto",
	)

	response_content: str | None = chat_completion.choices[0].message.content
	if response_content is None:
		raise ValueError("OpenAI API returned empty content")
	# At this point, mypy knows response_content is str (not None)
	return str(response_content)
