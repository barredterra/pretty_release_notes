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
			if line.original_pr and line.original_pr.reviewers:
				reviewers.update(line.original_pr.reviewers)
				if line.original_pr.merged_by not in (line.original_pr.author, line.pr.author):
					reviewers.add(line.original_pr.merged_by)
			if line.pr and line.pr.reviewers:
				reviewers.update(line.pr.reviewers)
				if line.pr.merged_by not in (line.pr.author, line.original_pr.author if line.original_pr else None):
					reviewers.add(line.pr.merged_by)

		return reviewers

	def serialize(self, exclude_pr_types: list[str] | None = None, exclude_pr_labels: set[str] | None = None) -> str:
		def is_exluded_type(pr):
			return pr.pr_type and pr.pr_type in exclude_pr_types

		def has_excluded_label(pr):
			return pr.labels and exclude_pr_labels and pr.labels & exclude_pr_labels

		if exclude_pr_types is None:
			exclude_pr_types = []

		lines = "\n".join(
			str(line)
			for line in self.lines
			if not line.pr or (not is_exluded_type(line.pr) and not has_excluded_label(line.pr))
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
