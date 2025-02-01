from openai import OpenAI


def get_chat_response(
	content: str, model: str, api_key: str,
) -> str:
	"""Get a chat response from OpenAI."""
	client = OpenAI(api_key=api_key)

	try:
		chat_completion = client.chat.completions.create(
			messages=[
				{
					"role": "user",
					"content": content,
				}
			],
			model=model,
		)
	except Exception as e:
		print("Error in OpenAI API", e)
		return ""

	return chat_completion.choices[0].message.content
