from pathlib import Path
from typing import TYPE_CHECKING

import typer
from dotenv import dotenv_values
from openai import OpenAI

from database import CSVDatabase, Database, SQLiteDatabase
from github import GitHubClient, Repository
from models import ReleaseNotes

if TYPE_CHECKING:
	from models import Issue, PullRequest

app = typer.Typer()
config = dotenv_values(".env")
DB_NAME = "stored_lines"


@app.command()
def main(repo: str, tag: str, owner: str = "frappe", database: bool = True):
	db = get_db() if database else None
	github = GitHubClient(config["GH_TOKEN"])
	repository = Repository(owner, repo)
	release = github.get_release(repository, tag)
	body = release["body"]
	print("-" * 4, "Original", "-" * 4)
	print(body)

	print("")
	print("-" * 4, "Processing PRs", "-" * 4)
	release_notes = ReleaseNotes.from_string(body)
	for i, line in enumerate(release_notes.lines):
		if not line.pr_no or line.is_new_contributor:
			print(line)
			continue

		pr = github.get_pr(repository, line.pr_no)
		if db:
			stored_sentence = db.get_sentence(repository, pr.backport_no or line.pr_no)
			if stored_sentence:
				release_notes.lines[i].sentence = stored_sentence
				print(release_notes.lines[i])
				continue

		pr_patch = github.get_text(pr.patch_url)
		if len(pr_patch) > int(config["MAX_PATCH_SIZE"]):
			pr_patch = "\n".join(
				commit["commit"]["message"]
				for commit in github.get_commit_messages(pr.commits_url)
			)

		closed_issues = github.get_closed_issues(
			repository, line.pr_no
		) or github.get_closed_issues(repository, pr.backport_no)

		pr_sentence = get_pr_sentence(
			pr,
			pr_patch,
			closed_issues[0] if closed_issues else None,
		)
		if not pr_sentence:
			continue

		pr_sentence = pr_sentence.lstrip(" -")
		if db:
			db.store_sentence(repository, pr.backport_no or line.pr_no, pr_sentence)
		release_notes.lines[i].sentence = pr_sentence
		print(release_notes.lines[i])

	print("")
	print("-" * 4, "Modified", "-" * 4)
	print(release_notes.serialize())


def get_pr_sentence(
	pr: "PullRequest", pr_patch: str, issue: "Issue | None" = None
) -> str:
	"""Get a single sentence to describe a PR."""
	client = OpenAI(
		# This is the default and can be omitted
		api_key=config["OPENAI_API_KEY"],
	)
	content = Path("prompt.txt").read_text()

	if issue:
		content += f"\n\n\n{issue}"

	content += f"\n\n\n{pr}\n\nPR Patch or commit messages: {pr_patch}"

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
