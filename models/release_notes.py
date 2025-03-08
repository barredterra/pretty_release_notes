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
			for author in {line.author for line in self.lines if line.author}
		)

		return f"{lines}\n\n**Authors**: {authors_string}"
