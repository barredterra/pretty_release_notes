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

	def serialize(self) -> str:
		return "\n".join(str(line) for line in self.lines)
