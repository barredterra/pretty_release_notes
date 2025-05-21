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
			if line.pr and line.pr.reviewers:
				reviewers.update(line.pr.reviewers)

		return reviewers

	def serialize(
		self,
		exclude_pr_types: list[str] | None = None,
		exclude_pr_labels: set[str] | None = None,
		exclude_authors: set[str] | None = None,
		model_name: str | None = None,
	) -> str:
		def is_exluded_type(pr):
			return pr.pr_type and pr.pr_type in exclude_pr_types

		def has_excluded_label(pr):
			return pr.labels and exclude_pr_labels and pr.labels & exclude_pr_labels

		if exclude_pr_types is None:
			exclude_pr_types = []

		if exclude_authors is None:
			exclude_authors = set()

		lines = "\n".join(
			str(line)
			for line in self.lines
			if not line.pr or (not is_exluded_type(line.pr) and not has_excluded_label(line.pr))
		)

		if model_name:
			lines += f"\n> [!NOTE]\n> These release notes were written by an LLM ({model_name}) and may contain errors.\n"

		authors_string = ", ".join(
			f"@{author}"
			for author in self.authors
			if author not in exclude_authors
		)

		reviewers_string = ", ".join(
			f"@{reviewer}"
			for reviewer in self.reviewers
		)

		if authors_string:
			lines += f"\n**Authors**: {authors_string}"
		if reviewers_string:
			lines += f"\n**Reviewers**: {reviewers_string}"

		return lines
