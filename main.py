from pathlib import Path
from typing import TYPE_CHECKING

import typer
from dotenv import dotenv_values
from requests import HTTPError

from database import CSVDatabase, Database, SQLiteDatabase
from github_client import GitHubClient
from models import ReleaseNotes, Repository
from openai_client import get_chat_response
from ui import CLI

if TYPE_CHECKING:
	from models import Issue, PullRequest

app = typer.Typer()
config = dotenv_values(".env")
DB_NAME = "stored_lines"


@app.command()
def main(repo: str, tag: str, owner: str | None = None, database: bool = True):
	ui = CLI()
	db = get_db() if database else None

	github = GitHubClient(config["GH_TOKEN"])
	repository = Repository(owner or config["DEFAULT_OWNER"] or "frappe", repo)
	exclude_pr_types = get_config_set("EXCLUDE_PR_TYPES")
	exclude_pr_labels = get_config_set("EXCLUDE_PR_LABELS")
	exclude_authors = get_config_set("EXCLUDE_AUTHORS")

	release = github.get_release(repository, tag)
	old_body = release["body"]
	ui.show_release_notes("Current Release Notes", old_body)

	try:
		gh_notes = github.generate_release_notes(repository, tag)
		new_body = gh_notes["body"]
		ui.show_release_notes("Regenerated by GitHub", new_body)
	except HTTPError as e:
		if e.response.status_code != 403:
			raise e

		ui.show_error(
			"No permission to regenerate release notes, trying to proceed with old ones."
		)
		new_body = old_body

	ui.show_markdown_text("# Rewriting ...")
	release_notes = ReleaseNotes.from_string(new_body)
	for line in release_notes.lines:
		if not line.pr_no or line.is_new_contributor:
			ui.show_markdown_text(str(line))
			continue

		line.pr = github.get_pr(repository, line.pr_no)

		if line.pr.pr_type in exclude_pr_types:
			continue

		if line.pr.labels and line.pr.labels & exclude_pr_labels:
			continue

		# Determine the actual reviewers.
		# An author who reviewed or merged their own PR or backport is not a reviewer.
		# A non-author who reviewed or merged someone else's PR is a reviewer.
		# The author of the original PR is also the author of the backport.
		line.pr.reviewers = github.get_pr_reviewers(repository, line.pr_no)
		line.pr.reviewers.add(line.pr.merged_by)
		line.pr.reviewers.discard(line.pr.author)
		line.pr.reviewers -= exclude_authors

		if line.pr.backport_no:
			line.original_pr = github.get_pr(repository, line.pr.backport_no)
			line.original_pr.reviewers = github.get_pr_reviewers(
				repository, line.pr.backport_no
			)
			line.original_pr.reviewers.add(line.original_pr.merged_by)
			line.original_pr.reviewers.discard(line.original_pr.author)
			line.original_pr.reviewers -= exclude_authors
			line.pr.reviewers.discard(line.original_pr.author)

		if db:
			stored_sentence = db.get_sentence(
				repository, line.pr.backport_no or line.pr_no
			)
			if stored_sentence:
				line.sentence = stored_sentence
				ui.show_markdown_text(str(line))
				continue

		pr_patch = github.get_text(line.pr.patch_url)
		if len(pr_patch) > int(config["MAX_PATCH_SIZE"]):
			pr_patch = "\n".join(
				commit["commit"]["message"]
				for commit in github.get_commit_messages(line.pr.commits_url)
			)

		closed_issues = github.get_closed_issues(repository, line.pr_no)
		if not closed_issues and line.pr.backport_no:
			closed_issues = github.get_closed_issues(repository, line.pr.backport_no)

		prompt = build_prompt(
			pr=line.pr,
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
			db.store_sentence(
				repository, line.pr.backport_no or line.pr_no, pr_sentence
			)
		line.sentence = pr_sentence
		ui.show_markdown_text(str(line))

	new_body = release_notes.serialize(
		exclude_pr_types, exclude_pr_labels, exclude_authors
	)

	ui.show_release_notes("New Release Notes", new_body)

	if ui.confirm_update():
		try:
			github.update_release(repository, release["id"], new_body)
			ui.show_success("Release notes updated successfully.")
		except HTTPError as e:
			if e.response.status_code != 403:
				raise e

			ui.show_error("No permission to update release notes, skipping.")


def build_prompt(pr: "PullRequest", pr_patch: str, issue: "Issue | None" = None) -> str:
	prompt = Path("prompt.txt").read_text()

	if issue:
		prompt += f"\n\n\n{issue}"

	prompt += f"\n\n\n{pr}\n\nPR Patch or commit messages: {pr_patch}"

	return prompt


def get_config_set(key: str) -> set[str]:
	return set(config[key].split(",")) if config[key] else set()


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
