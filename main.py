import re
from pathlib import Path

import typer
from dotenv import dotenv_values
from openai import OpenAI

from github import GitHubClient

app = typer.Typer()
config = dotenv_values(".env")
pr_re = re.compile(r"pull/(\d+)")  # reqex to find PR number


@app.command()
def main(repo: str, tag: str, owner: str = "frappe"):
	github = GitHubClient(config["GH_TOKEN"])
	release = github.get_release(owner, repo, tag)
	body = release["body"]
	print("-" * 4, "Original", "-" * 4)
	print(body)
	print("")
	print("-" * 4, "Modified", "-" * 4)
	body_lines = body.split("\n")
	for i, line in enumerate(body_lines.copy()):
		if not line.startswith("* "):
			continue
		line = line[2:]
		match = pr_re.search(line)
		if not match:
			continue
		pr_no = match.group(1)
		pr = github.get_pr(owner, repo, pr_no)
		pr_web_url = pr["html_url"]
		pr_title = pr["title"]
		pr_body = pr["body"]
		pr_patch = github.get_text(pr["patch_url"])
		if len(pr_patch) > int(config["MAX_PATCH_SIZE"]):
			pr_patch = "\n".join(
				commit["commit"]["message"]
				for commit in github.get_commit_messages(pr["commits_url"])
			)
		pr_sentence = get_pr_sentence(pr_title, pr_body, pr_patch)
		if pr_sentence:
			pr_sentence = pr_sentence.lstrip(" -")
			body_lines[i] = f"* {pr_sentence} {pr_web_url}"

		print(body_lines[i])

	# print remaining lines
	for x in range(i - 1, len(body_lines)):
		print(body_lines[x])


def get_pr_sentence(pr_title: str, pr_body: str, pr_patch: str) -> str:
	"""Get a single sentence to describe a PR."""
	client = OpenAI(
		# This is the default and can be omitted
		api_key=config["OPENAI_API_KEY"],
	)
	prompt = Path("prompt.txt").read_text()

	try:
		chat_completion = client.chat.completions.create(
			messages=[
				{
					"role": "user",
					"content": f"""{prompt}\n\nPR Title: {pr_title}\n\nPR Body: {pr_body}\n\nPR Patch or commit messages: {pr_patch}""",
				}
			],
			model=config["OPENAI_MODEL"],
		)
	except:
		print("Error in OpenAI API")
		return ""

	return chat_completion.choices[0].message.content


if __name__ == "__main__":
	app()
