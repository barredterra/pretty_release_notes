import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .change import Change

if TYPE_CHECKING:
	from github_client import GitHubClient
	from models.repository import Repository


CONVENTIONAL_TYPE_AND_SCOPE = re.compile(r"^([a-zA-Z]+)(?:\(([^)]+)\))?:\s+(.+)")


@dataclass
class Commit(Change):
	github: "GitHubClient"
	repository: "Repository"
	id: str  # sha
	message: str
	author: str
	labels: set[str] | None = None

	@property
	def url(self) -> str:
		return f"{self.repository.url}/commit/{self.id}"

	@property
	def diff_url(self) -> str:
		return f"{self.url}.patch"

	@property
	def conventional_type(self) -> str | None:
		commit_type_match = CONVENTIONAL_TYPE_AND_SCOPE.search(self.message)
		return commit_type_match.group(1) if commit_type_match else None

	def get_prompt(self, prompt_template: str, max_patch_size: int) -> str:
		prompt = prompt_template

		changes = self._get_changes(max_patch_size)
		prompt += f"\n\n\n{self}\n\nDiff: {changes}"

		return prompt

	def get_reviewers(self) -> set[str]:
		return set()

	def get_author(self) -> str:
		return self.author

	def _get_changes(self, max_patch_size: int) -> str:
		"""Return the diff if it is not too large. Otherwise, return a truncated diff."""
		diff = self._get_diff()
		if len(diff) > max_patch_size:
			return f"{diff[: max_patch_size - 13]}\n\n[TRUNCATED]"

		return diff

	def _get_diff(self) -> str:
		"""Get the diff for this commit."""
		return self.github.get_commit_diff(self.repository, self.id)

	@classmethod
	def from_dict(
		cls, github: "GitHubClient", repository: "Repository", data: dict
	) -> "Commit":
		return cls(
			github=github,
			repository=repository,
			id=data["sha"],
			message=data["commit"]["message"],
			author=data["author"]["login"],
		)

	def __str__(self):
		return f"""Commit Message: {self.message}"""
