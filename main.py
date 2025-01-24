import re
from pathlib import Path

import typer
from dotenv import dotenv_values
from openai import OpenAI

from github import GitHubClient
from release_notes import ReleaseNotes
from database import Database, CSVDatabase, SQLiteDatabase

app = typer.Typer()
config = dotenv_values(".env")
DB_NAME = "stored_lines"


@app.command()
def main(repo: str, tag: str, owner: str = "frappe"):
	db = get_db()
	github = GitHubClient(config["GH_TOKEN"])
	release = github.get_release(owner, repo, tag)
	body = release["body"]
	print("-" * 4, "Original", "-" * 4)
	print(body)

	print("")
	print("-" * 4, "Processing PRs", "-" * 4)
	release_notes = ReleaseNotes()
	release_notes.parse(body)
	for i, (sentence, pr_url, pr_no) in enumerate(release_notes.whats_changed):
		if not pr_no:
			print(release_notes.format_line(i))
			continue

		pr = github.get_pr(owner, repo, pr_no)
		pr_title = pr["title"]

		original_pr_no = None
		original_pr_match = re.search(r"\(backport #(\d+)\)", pr_title)
		if original_pr_match:
			original_pr_no = original_pr_match[1]

		stored_sentence = db.get_sentence(owner, repo, original_pr_no or pr_no)
		if stored_sentence:
			release_notes.whats_changed[i][0] = stored_sentence
			print(release_notes.format_line(i))
			continue

		pr_body = pr["body"]
		pr_patch = github.get_text(pr["patch_url"])
		if len(pr_patch) > int(config["MAX_PATCH_SIZE"]):
			pr_patch = "\n".join(
				commit["commit"]["message"]
				for commit in github.get_commit_messages(pr["commits_url"])
			)

		closed_issues = github.get_closed_issues(owner, repo, pr_no) or github.get_closed_issues(owner, repo, original_pr_no)

		issue_body = None
		issue_title = None
		if closed_issues:
			issue_body = closed_issues[0]["node"]["body"]
			issue_title = closed_issues[0]["node"]["title"]

		pr_sentence = get_pr_sentence(pr_title, pr_body, pr_patch, issue_body, issue_title)
		if pr_sentence:
			pr_sentence = pr_sentence.lstrip(" -")
			db.store_sentence(owner, repo, original_pr_no or pr_no, pr_sentence)
			release_notes.whats_changed[i][0] = pr_sentence
			print(release_notes.format_line(i))

	print("")
	print("-" * 4, "Modified", "-" * 4)
	print(release_notes.serialize())


def get_pr_sentence(pr_title: str, pr_body: str, pr_patch: str, issue_body: str, issue_title: str) -> str:
	"""Get a single sentence to describe a PR."""
	client = OpenAI(
		# This is the default and can be omitted
		api_key=config["OPENAI_API_KEY"],
	)
	prompt = Path("prompt.txt").read_text()
	pr_text = f"""PR Title: {pr_title}\n\nPR Body: {pr_body}\n\nPR Patch or commit messages: {pr_patch}"""
	issue_text = f"""Issue Title: {issue_title}\n\nIssue Body: {issue_body}""" if issue_title and issue_body else ""
	content = prompt

	if issue_text:
		content += f"\n\n\n{issue_text}"

	content += f"\n\n\n{pr_text}"

	try:
		chat_completion = client.chat.completions.create(
			messages=[
				{
					"role": "user",
					"content": content,
				}
			],
			model=config["OPENAI_MODEL"],
		)
	except Exception as e:
		print("Error in OpenAI API", e)
		return ""

	return chat_completion.choices[0].message.content


def get_db() -> Database:
	db_type = config["DB_TYPE"]
	db_path = Path(DB_NAME)

	if db_type == "csv":
		return CSVDatabase(db_path.with_suffix(".csv"))
	elif db_type == "sqlite":
		return SQLiteDatabase(db_path.with_suffix(".sqlite"))
	else:
		raise ValueError(f"Invalid database type: {db_type}")


if __name__ == "__main__":
	app()
