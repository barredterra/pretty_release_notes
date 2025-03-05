import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from models.repository import Repository


@dataclass
class PullRequest:
	repository: "Repository"
	number: int
	title: str
	body: str
	patch_url: str
	commits_url: str | None = None
	author: str | None = None

	@property
	def url(self):
		return f"{self.repository.url}/pull/{self.number}"

	@property
	def backport_no(self) -> str | None:
		original_pr_match = re.search(r"\(backport #(\d+)\)", self.title)
		return original_pr_match[1] if original_pr_match else None

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
		)

	def __str__(self):
		return f"""PR Title: {self.title}\n\nPR Body: {self.body}"""
