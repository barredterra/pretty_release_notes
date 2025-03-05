from dataclasses import dataclass
import re

REGEX_PR_URL = re.compile(
	r"https://github.com/[^/]+/[^/]+/pull/(\d+)"
)
CONVENTIONAL_TYPE_AND_SCOPE = re.compile(
	r"^\* ([a-zA-Z]+)(?:\(([^)]+)\))?:\s+(.+)$"
)


@dataclass
class ReleaseNotesLine:
	original_line: str
	pr_url: str | None = None
	pr_no: str | None = None
	is_new_contributor: bool = False
	sentence: str | None = None
	pr_type: str | None = None

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

		pr_type_match = CONVENTIONAL_TYPE_AND_SCOPE.search(line)
		pr_type = pr_type_match.group(1) if pr_type_match else None

		is_new_contributor = "made their first contribution" in line

		return cls(
			original_line=line,
			pr_url=pr_url,
			pr_no=pr_no,
			is_new_contributor=is_new_contributor,
			pr_type=pr_type,
		)
