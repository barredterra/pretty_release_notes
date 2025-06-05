import re
from dataclasses import dataclass

from models.commit import Commit
from models.pull_request import PullRequest

REGEX_PR_URL = re.compile(r"https://github.com/[^/]+/[^/]+/pull/(\d+)")


@dataclass
class ReleaseNotesLine:
	original_line: str
	pr_url: str | None = None
	pr_no: str | None = None
	change: "PullRequest | Commit | None" = None
	is_new_contributor: bool = False
	sentence: str | None = None
	author: str | None = None

	def __str__(self):
		if self.sentence and self.pr_url:
			return f"""* {self.sentence} ({self.pr_url})"""

		return self.original_line

	@classmethod
	def from_string(cls, line: str) -> "ReleaseNotesLine":
		"""Parse the PR URL into a string."""
		pr_match = REGEX_PR_URL.search(line)
		pr_url = pr_match.group(0) if pr_match else None
		pr_no = pr_match.group(1) if pr_match else None

		is_new_contributor = "made their first contribution" in line

		return cls(
			original_line=line,
			pr_url=pr_url,
			pr_no=pr_no,
			is_new_contributor=is_new_contributor,
		)
