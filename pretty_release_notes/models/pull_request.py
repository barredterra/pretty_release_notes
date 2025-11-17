import re
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._utils import get_conventional_type
from .change import Change

if TYPE_CHECKING:
	from pretty_release_notes.github_client import GitHubClient
	from pretty_release_notes.models.issue import Issue
	from pretty_release_notes.models.repository import Repository


BACKPORT_NO = re.compile(r"\(backport #(\d+)\)\s*$")
REVERT_PATTERNS = [
	re.compile(r"[Rr]everts\s+[\w-]+/[\w-]+#(\d+)"),
	re.compile(r"[Rr]everts\s+https://github\.com/[\w-]+/[\w-]+/pull/(\d+)"),
	re.compile(r"[Rr]everts\s+#(\d+)"),
]


@dataclass
class PullRequest(Change):
	github: "GitHubClient"
	repository: "Repository"
	id: int  # number
	title: str
	body: str
	html_url: str
	commits_url: str | None = None
	author: str = ""
	merged_by: str | None = None
	labels: set[str] | None = None
	backport_of: "PullRequest | None" = None
	reviewers: set[str] | None = None

	@property
	def backport_no(self) -> str | None:
		"""Extract the backport number from the title.

		Examples:
		'feat(regional): Address Template for Germany & Switzerland (backport #46737)' -> '46737'
		'Revert "perf: timeout while renaming cost center (backport #46641)" (backport #46749)' -> '46749'
		"""
		match = BACKPORT_NO.search(self.title)
		return match.group(1) if match else None

	@property
	def is_revert(self) -> bool:
		"""Check if this PR is a revert of another PR."""
		if not self.body:
			return False
		return any(pattern.search(self.body) for pattern in REVERT_PATTERNS)

	@property
	def reverted_pr_number(self) -> str | None:
		"""Extract the PR number being reverted from the body.

		Returns the PR number as a string, or None if this is not a revert.
		"""
		if not self.body:
			return None

		for pattern in REVERT_PATTERNS:
			match = pattern.search(self.body)
			if match:
				return match.group(1)

		return None

	@property
	def conventional_type(self) -> str | None:
		"""Extract the conventional type from the title.

		Examples:
		'feat(regional): Address Template for Germany & Switzerland' -> 'feat'
		'Revert "perf: timeout while renaming cost center"' -> None
		"""
		return get_conventional_type(self.title)

	def get_prompt(self, prompt_template: str, max_patch_size: int) -> str:
		prompt = prompt_template

		closed_issues = self.get_closed_issues()
		if closed_issues:
			prompt += f"\n\n\n{closed_issues[0]}"

		changes = self._get_changes(max_patch_size)
		prompt += f"\n\n\n{self}\n\nPR Patch or commit messages: {changes}"

		return prompt

	def set_reviewers(self) -> set[str]:
		"""Determine the actual reviewers for a PR.

		An author who reviewed or merged their own PR or backport is not a reviewer.
		A non-author who reviewed or merged someone else's PR is a reviewer.
		The author of the original PR is also the author of the backport.
		"""
		threads = [
			threading.Thread(target=self._get_reviewers),
			threading.Thread(target=self._get_original_reviewers),
		]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join()

		reviewers = self.reviewers.copy() if self.reviewers else set()
		if self.merged_by:
			reviewers.add(self.merged_by)
		reviewers.discard(self.author)

		if self.backport_of and self.backport_of.reviewers:
			reviewers.update(self.backport_of.reviewers)
			reviewers.discard(self.backport_of.author)

		self.reviewers = reviewers
		return self.reviewers

	def get_author(self) -> str:
		return self.backport_of.author if self.backport_of else self.author

	def get_summary_key(self) -> str:
		# Keep in mind that this needs to work before `self.backport_of` is initialised
		return self.backport_no or str(self.id)

	def _get_reviewers(self) -> None:
		"""Get the reviewers for a PR."""
		self.reviewers = self.github.get_pr_reviewers(self.repository, str(self.id))

	def _get_original_reviewers(self) -> None:
		"""Get the reviewers for the original PR."""
		self._set_backport_of()
		if self.backport_of:
			self.backport_of.set_reviewers()

	def _get_changes(self, max_patch_size: int) -> str:
		"""Get the changes for a PR.

		Return the patch if it is not too large. Otherwise, return the commit messages.
		"""
		changes = self._get_patch()
		if not changes or len(changes) > max_patch_size:
			changes = "\n".join(self._get_commit_messages())

		return changes

	def _get_patch(self) -> str:
		"""Return the patch for a PR."""
		return self.github.get_pr_patch(self.repository, str(self.id))

	def _get_commit_messages(self) -> list[str]:
		"""Get the commit messages for a PR."""
		if not self.commits_url:
			return []
		return self.github.get_commit_messages(self.commits_url)

	def get_closed_issues(self) -> list["Issue"]:
		"""Return the issues closed by this PR or backport."""
		issues = self._get_closed_issues()
		self._set_backport_of()
		if not issues and self.backport_of:
			issues = self.backport_of._get_closed_issues()
		return issues

	def _get_closed_issues(self) -> list["Issue"]:
		return self.github.get_closed_issues(self.repository, str(self.id))

	def _set_backport_of(self):
		if not self.backport_no or self.backport_of:
			return

		self.backport_of = self.github.get_pr(self.repository, self.backport_no)

	@classmethod
	def from_dict(cls, github: "GitHubClient", repository: "Repository", data: dict) -> "PullRequest":
		return cls(
			github=github,
			repository=repository,
			id=data["number"],
			title=data["title"],
			body=data["body"],
			html_url=data["html_url"],
			commits_url=data["commits_url"],
			author=data["user"]["login"],
			merged_by=data["merged_by"]["login"],
			labels={label["name"] for label in data["labels"]},
		)

	def __str__(self):
		return f"""PR Title: {self.title}\n\nPR Body: {self.body}"""
