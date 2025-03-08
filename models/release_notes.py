from dataclasses import dataclass
from .release_notes_line import ReleaseNotesLine


@dataclass
class ReleaseNotes:
	"""Parse release notes into structured data."""
	lines: list[ReleaseNotesLine]

	@classmethod
	def from_string(cls, release_notes: str) -> "ReleaseNotes":
		return cls(
			lines = [
				ReleaseNotesLine.from_string(line)
				for line in release_notes.split("\n")
			]
		)

	@property
	def authors(self) -> set[str]:
		return {
			line.original_pr.author if line.original_pr else line.pr.author
			for line in self.lines
			if line.original_pr or line.pr
		}

	@property
	def reviewers(self) -> set[str]:
		reviewers = set()
		for line in self.lines:
			if line.original_pr:
				reviewers.update(line.original_pr.reviewers)
				if line.original_pr.merged_by not in (line.original_pr.author, line.pr.author):
					reviewers.add(line.original_pr.merged_by)
			if line.pr:
				reviewers.update(line.pr.reviewers)
				if line.pr.merged_by not in (line.pr.author, line.original_pr.author if line.original_pr else None):
					reviewers.add(line.pr.merged_by)

		return reviewers

	def serialize(self, exclude_pr_types: list[str] | None = None) -> str:
		if exclude_pr_types is None:
			exclude_pr_types = []

		lines = "\n".join(
			str(line)
			for line in self.lines
			if not line.pr or not line.pr.pr_type or line.pr.pr_type not in exclude_pr_types
		)

		authors_string = ", ".join(
			f"@{author}"
			for author in self.authors
		)

		reviewers_string = ", ".join(
			f"@{reviewer}"
			for reviewer in self.reviewers
		)

		notes = f"{lines}\n**Authors**: {authors_string}"
		if reviewers_string:
			notes += f"\n**Reviewers**: {reviewers_string}"

		return notes
