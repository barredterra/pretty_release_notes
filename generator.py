from pathlib import Path
from typing import TYPE_CHECKING

from requests import HTTPError

from database import get_db
from github_client import GitHubClient
from models import ReleaseNotes, Repository
from openai_client import get_chat_response

if TYPE_CHECKING:
	from models import Issue, PullRequest, ReleaseNotesLine
	from ui import CLI


class ReleaseNotesGenerator:
	def __init__(
		self,
		owner: str,
		repo: str,
		prompt_path: Path,
		github_token: str,
		openai_api_key: str,
		openai_model: str = "gpt-4.1",
		exclude_pr_types: set[str] | None = None,
		exclude_pr_labels: set[str] | None = None,
		exclude_authors: set[str] | None = None,
		db_type: str = "sqlite",
		db_name: str = "stored_lines",
		use_db: bool = True,
		ui: "CLI | None" = None,
		max_patch_size: int = 10000,
	):
		self.github = GitHubClient(github_token)
		self.repository = Repository(owner, repo)
		self.exclude_pr_types = exclude_pr_types or set()
		self.exclude_pr_labels = exclude_pr_labels or set()
		self.exclude_authors = exclude_authors or set()
		self.openai_api_key = openai_api_key
		self.openai_model = openai_model
		self.max_patch_size = max_patch_size
		self.prompt_path = prompt_path
		self.ui = ui
		self.db = get_db(db_type, db_name) if use_db else None

	def generate(self, tag: str):
		"""Generate release notes for a given tag."""
		release = self._get_release(tag)
		old_body = release["body"]

		if self.ui:
			self.ui.show_release_notes("Current Release Notes", old_body)

		try:
			gh_notes = self.github.generate_release_notes(self.repository, tag)
			new_body = gh_notes["body"]
			if self.ui:
				self.ui.show_release_notes("Regenerated by GitHub", new_body)
		except HTTPError as e:
			if e.response.status_code != 403:
				raise e

			if self.ui:
				self.ui.show_error(
					"No permission to regenerate release notes, trying to proceed with old ones."
				)
			new_body = old_body

		if self.ui:
			self.ui.show_markdown_text("# Rewriting ...")

		release_notes = ReleaseNotes.from_string(new_body)
		for line in release_notes.lines:
			self._process_line(line)

		return release_notes.serialize(
			self.exclude_pr_types,
			self.exclude_pr_labels,
			self.exclude_authors,
			model_name=f"OpenAI {self.openai_model}",
		)

	def update_on_github(self, new_body: str, tag: str):
		"""Update release notes on GitHub."""
		release = self._get_release(tag)
		try:
			self.github.update_release(self.repository, release["id"], new_body)
			if self.ui:
				self.ui.show_success("Release notes updated successfully.")
		except HTTPError as e:
			if e.response.status_code != 403:
				raise e

			if self.ui:
				self.ui.show_error("No permission to update release notes, skipping.")

	def _process_line(self, line: "ReleaseNotesLine"):
		if not line.pr_no or line.is_new_contributor:
			if self.ui:
				self.ui.show_markdown_text(str(line))
			return

		line.pr = self.github.get_pr(self.repository, line.pr_no)

		if line.pr.pr_type in self.exclude_pr_types:
			return

		if line.pr.labels and line.pr.labels & self.exclude_pr_labels:
			return

		self._set_reviewers(line)

		if self.db:
			stored_sentence = self.db.get_sentence(
				self.repository, line.pr.backport_no or line.pr_no
			)
			if stored_sentence:
				line.sentence = stored_sentence
				if self.ui:
					self.ui.show_markdown_text(str(line))
				return

		pr_patch = self.github.get_text(line.pr.patch_url)
		if len(pr_patch) > self.max_patch_size:
			pr_patch = "\n".join(self._get_commit_messages(line.pr.commits_url))

		closed_issues = self.github.get_closed_issues(self.repository, line.pr_no)
		if not closed_issues and line.pr.backport_no:
			closed_issues = self.github.get_closed_issues(
				self.repository, line.pr.backport_no
			)

		prompt = self._build_prompt(
			pr=line.pr,
			pr_patch=pr_patch,
			issue=closed_issues[0] if closed_issues else None,
		)
		pr_sentence = get_chat_response(
			content=prompt,
			model=self.openai_model,
			api_key=self.openai_api_key,
		)
		if not pr_sentence:
			return

		pr_sentence = pr_sentence.lstrip(" -")
		if self.db:
			self.db.store_sentence(
				self.repository, line.pr.backport_no or line.pr_no, pr_sentence
			)
		line.sentence = pr_sentence
		if self.ui:
			self.ui.show_markdown_text(str(line))

	def _set_reviewers(self, line: "ReleaseNotesLine"):
		"""Determine the actual reviewers for a PR.

		An author who reviewed or merged their own PR or backport is not a reviewer.
		A non-author who reviewed or merged someone else's PR is a reviewer.
		The author of the original PR is also the author of the backport.
		"""
		line.pr.reviewers = self.github.get_pr_reviewers(
			self.repository, line.pr_no
		)
		line.pr.reviewers.add(line.pr.merged_by)
		line.pr.reviewers.discard(line.pr.author)
		line.pr.reviewers -= self.exclude_authors

		if line.pr.backport_no:
			line.original_pr = self.github.get_pr(
				self.repository, line.pr.backport_no
			)
			line.original_pr.reviewers = self.github.get_pr_reviewers(
				self.repository, line.pr.backport_no
			)
			line.original_pr.reviewers.add(line.original_pr.merged_by)
			line.original_pr.reviewers.discard(line.original_pr.author)
			line.original_pr.reviewers -= self.exclude_authors
			line.pr.reviewers.discard(line.original_pr.author)

	def _get_release(self, tag: str):
		return self.github.get_release(self.repository, tag)

	def _get_commit_messages(self, url: str):
		return [commit["commit"]["message"] for commit in self.github.get_commit_messages(url)]

	def _build_prompt(self, pr: "PullRequest", pr_patch: str, issue: "Issue | None" = None) -> str:
		prompt = self.prompt_path.read_text()

		if issue:
			prompt += f"\n\n\n{issue}"

		prompt += f"\n\n\n{pr}\n\nPR Patch or commit messages: {pr_patch}"

		return prompt
