from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
	from pretty_release_notes.github_client import GitHubClient
	from pretty_release_notes.models.repository import Repository


class Change(Protocol):
	github: "GitHubClient"
	repository: "Repository"
	author: str
	labels: set[str] | None
	reviewers: set[str] | None

	@property
	def conventional_type(self) -> str | None:
		"""Extract the conventional type from the change."""
		...

	def get_prompt(self, prompt_template: str, max_patch_size: int) -> str:
		"""Return the prompt used for summarising this change."""
		...

	def set_reviewers(self) -> set[str]:
		"""Set the reviewers of this change and the original change that this is a backport of."""
		...

	def get_author(self) -> str:
		"""Return the author of this change, or of the original change that this is a backport of."""
		...

	def get_summary_key(self) -> str:
		"""Return the key used for storing the summary in the database."""
		...
