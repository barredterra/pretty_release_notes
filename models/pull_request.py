import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .change import Change
from ._utils import get_conventional_type

if TYPE_CHECKING:
	from github_client import GitHubClient
	from models.issue import Issue
	from models.repository import Repository


CONVENTIONAL_TYPE_AND_SCOPE = re.compile(r"^([a-zA-Z]+)(?:\(([^)]+)\))?:\s+(.+)$")


@dataclass
class PullRequest(Change):
	github: "GitHubClient"
	repository: "Repository"
	id: int  # number
	title: str
	body: str
	patch_url: str
	commits_url: str | None = None
	author: str | None = None
	merged_by: str | None = None
	labels: set[str] | None = None
	backport_of: "PullRequest | None" = None

	@property
	def url(self):
		return f"{self.repository.url}/pull/{self.id}"

	@property
	def backport_no(self) -> str | None:
		"""Extract the backport number from the title.

		Examples:
		'feat(regional): Address Template for Germany & Switzerland (backport #46737)' -> '46737'
		'Revert "perf: timeout while renaming cost center (backport #46641)" (backport #46749)' -> '46749'
		"""
		original_pr_match = re.search(r"\(backport #(\d+)\)\s*$", self.title)
		return original_pr_match[1] if original_pr_match else None

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

	def get_reviewers(self) -> set[str]:
		"""Determine the actual reviewers for a PR.

		An author who reviewed or merged their own PR or backport is not a reviewer.
		A non-author who reviewed or merged someone else's PR is a reviewer.
		The author of the original PR is also the author of the backport.
		"""
		reviewers = self.github.get_pr_reviewers(self.repository, self.id)
		reviewers.add(self.merged_by)
		reviewers.discard(self.author)

		self._set_backport_of()
		if self.backport_of:
			reviewers.update(self.backport_of.get_reviewers())
			reviewers.discard(self._get_original_author())

		return reviewers

	def get_author(self) -> str:
		return self._get_original_author() or self.author

	def get_summary_key(self) -> str:
		# Keep in mind that this needs to work before `self.backport_of` is initialised
		return self.backport_no or self.id

	def _get_original_author(self) -> str:
		self._set_backport_of()
		return self.backport_of.get_author() if self.backport_of else None

	def _get_changes(self, max_patch_size: int) -> str:
		"""Get the changes for a PR.

		Return the patch if it is not too large. Otherwise, return the commit messages.
		"""
		changes = self._get_patch()
		if len(changes) > max_patch_size:
			changes = "\n".join(self._get_commit_messages())

		return changes

	def _get_patch(self) -> str:
		"""Return the patch for a PR."""
		return self.github.get_pr_patch(self.repository, self.id)

	def _get_commit_messages(self) -> list[str]:
		"""Get the commit messages for a PR."""
		return self.github.get_commit_messages(self.commits_url)

	def get_closed_issues(self) -> list["Issue"]:
		"""Return the issues closed by this PR or backport."""
		issues = self._get_closed_issues()
		self._set_backport_of()
		if not issues and self.backport_of:
			issues = self.backport_of._get_closed_issues()
		return issues

	def _get_closed_issues(self) -> list["Issue"]:
		return self.github.get_closed_issues(self.repository, self.id)

	def _set_backport_of(self):
		if not self.backport_no or self.backport_of:
			return

		self.backport_of = self.github.get_pr(self.repository, self.backport_no)

	@classmethod
	def from_dict(
		cls, github: "GitHubClient", repository: "Repository", data: dict
	) -> "PullRequest":
		return cls(
			github=github,
			repository=repository,
			id=data["number"],
			title=data["title"],
			body=data["body"],
			patch_url=data["patch_url"],
			commits_url=data["commits_url"],
			author=data["user"]["login"],
			merged_by=data["merged_by"]["login"],
			labels={label["name"] for label in data["labels"]},
		)

	def __str__(self):
		return f"""PR Title: {self.title}\n\nPR Body: {self.body}"""
