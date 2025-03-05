from pathlib import Path
from typing import TYPE_CHECKING

from requests import HTTPError
import typer
from dotenv import dotenv_values

from database import CSVDatabase, Database, SQLiteDatabase
from github_client import GitHubClient
from models import ReleaseNotes, Repository
from openai_client import get_chat_response

if TYPE_CHECKING:
	from models import Issue, PullRequest

app = typer.Typer()
config = dotenv_values(".env")
DB_NAME = "stored_lines"


@app.command()
def main(repo: str, tag: str, owner: str | None = None, database: bool = True):
	db = get_db() if database else None
	github = GitHubClient(config["GH_TOKEN"])
	repository = Repository(owner or config["DEFAULT_OWNER"] or "frappe", repo)
	release = github.get_release(repository, tag)
	old_body = release["body"]
	print("-" * 4, "Original", "-" * 4)
	print(old_body)

	try:
		gh_notes = github.generate_release_notes(repository, tag)
		new_body = gh_notes["body"]
		print("-" * 4, "Generated", "-" * 4)
		print(new_body)
	except HTTPError as e:
		if e.response.status_code != 403:
			raise e

		print("No permission to regenerate release notes, trying to proceed with old ones.")
		new_body = old_body

	print("")
	print("-" * 4, "Processing PRs", "-" * 4)
	release_notes = ReleaseNotes.from_string(new_body)
	for line in release_notes.lines:
		if not line.pr_no or line.is_new_contributor:
			print(line)
			continue

		pr = github.get_pr(repository, line.pr_no)
		if db:
			stored_sentence = db.get_sentence(repository, pr.backport_no or line.pr_no)
			if stored_sentence:
				line.sentence = stored_sentence
				print(line)
				continue

		pr_patch = github.get_text(pr.patch_url)
		if len(pr_patch) > int(config["MAX_PATCH_SIZE"]):
			pr_patch = "\n".join(
				commit["commit"]["message"]
				for commit in github.get_commit_messages(pr.commits_url)
			)

		closed_issues = github.get_closed_issues(repository, line.pr_no)
		if not closed_issues and pr.backport_no:
			closed_issues = github.get_closed_issues(repository, pr.backport_no)

		prompt = build_prompt(
			pr=pr,
			pr_patch=pr_patch,
			issue=closed_issues[0] if closed_issues else None,
		)
		pr_sentence = get_chat_response(
			content=prompt,
			model=config["OPENAI_MODEL"],
			api_key=config["OPENAI_API_KEY"],
		)
		if not pr_sentence:
			continue

		pr_sentence = pr_sentence.lstrip(" -")
		if db:
			db.store_sentence(repository, pr.backport_no or line.pr_no, pr_sentence)
		line.sentence = pr_sentence
		print(line)

	new_body = release_notes.serialize()

	print("")
	print("-" * 4, "Modified", "-" * 4)
	print(new_body)

	if typer.confirm("Update release notes?"):
		try:
			github.update_release(repository, release["id"], new_body)
		except HTTPError as e:
			if e.response.status_code != 403:
				raise e

			print("No permission to update release notes, skipping.")


def build_prompt(pr: "PullRequest", pr_patch: str, issue: "Issue | None" = None) -> str:
	prompt = Path("prompt.txt").read_text()

	if issue:
		prompt += f"\n\n\n{issue}"

	prompt += f"\n\n\n{pr}\n\nPR Patch or commit messages: {pr_patch}"

	return prompt


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
