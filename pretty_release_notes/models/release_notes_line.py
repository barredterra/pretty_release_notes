import re
from dataclasses import dataclass

from .commit import Commit
from .pull_request import PullRequest

REGEX_PR_URL = re.compile(r"https://github.com/[^/]+/[^/]+/pull/(\d+)")


@dataclass
class ReleaseNotesLine:
	original_line: str
	pr_no: str | None = None
	change: "PullRequest | Commit | None" = None
	is_new_contributor: bool = False
	sentence: str | None = None

	def __str__(self):
		if self.sentence:
			return f"""* {self.sentence} ({self.change.html_url})"""

		return self.original_line

	@classmethod
	def from_string(cls, line: str) -> "ReleaseNotesLine":
		"""Parse the PR URL into a string."""
		pr_match = REGEX_PR_URL.search(line)
		pr_no = pr_match.group(1) if pr_match else None

		is_new_contributor = "made their first contribution" in line

		return cls(
			original_line=line,
			pr_no=pr_no,
			is_new_contributor=is_new_contributor,
		)
