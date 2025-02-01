from dataclasses import dataclass
import re

REGEX_PR_URL = re.compile(
	r"https://github.com/[^/]+/[^/]+/pull/(\d+)"
) 


@dataclass
class ReleaseNotesLine:
	original_line: str
	sentence: str | None = None
	pr_url: str | None = None
	pr_no: str | None = None

	def __str__(self):
		if self.sentence and self.pr_url:
			return f"""* {self.sentence} ({self.pr_url})"""

		return self.original_line

	def parse_line(self):
		"""Parse the PR URL into a string."""
		pr_match = REGEX_PR_URL.search(self.original_line)
		self.pr_url = pr_match.group(0) if pr_match else None
		self.pr_no = pr_match.group(1) if pr_match else None
