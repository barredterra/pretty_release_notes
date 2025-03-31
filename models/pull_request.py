import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from models.repository import Repository


CONVENTIONAL_TYPE_AND_SCOPE = re.compile(
	r"^([a-zA-Z]+)(?:\(([^)]+)\))?:\s+(.+)$"
)


@dataclass
class PullRequest:
	repository: "Repository"
	number: int
	title: str
	body: str
	patch_url: str
	commits_url: str | None = None
	author: str | None = None
	reviewers: set[str] | None = None
	merged_by: str | None = None
	labels: set[str] | None = None

	@property
	def url(self):
		return f"{self.repository.url}/pull/{self.number}"

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
	def pr_type(self) -> str | None:
		pr_type_match = CONVENTIONAL_TYPE_AND_SCOPE.search(self.title)
		return pr_type_match.group(1) if pr_type_match else None

	@classmethod
	def from_dict(cls, repository: "Repository", data: dict) -> "PullRequest":
		return cls(
			repository=repository,
			number=data["number"],
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
