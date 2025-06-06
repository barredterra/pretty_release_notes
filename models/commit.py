from dataclasses import dataclass
from typing import TYPE_CHECKING

from ._utils import get_conventional_type
from .change import Change

if TYPE_CHECKING:
	from github_client import GitHubClient
	from models.repository import Repository


@dataclass
class Commit(Change):
	github: "GitHubClient"
	repository: "Repository"
	id: str  # sha
	message: str
	author: str
	html_url: str
	labels: set[str] | None = None

	@property
	def conventional_type(self) -> str | None:
		return get_conventional_type(self.message)

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
			html_url=data["html_url"],
		)

	def __str__(self):
		return f"""Commit Message: {self.message}"""
