from dataclasses import dataclass
from .release_notes_line import ReleaseNotesLine


@dataclass
class ReleaseNotes:
	"""Parse release notes into structured data."""
	whats_changed: list[ReleaseNotesLine]
	new_contributors: list[str]
	full_changelog: str

	@classmethod
	def from_string(cls, release_notes: str) -> "ReleaseNotes":
		whats_changed = []
		new_contributors = []
		full_changelog = ""

		in_whats_changed = False
		in_new_contributors = False
		for line in release_notes.split("\n"):
			if not line.strip():
				continue

			if line.strip() == "## What's Changed":
				in_whats_changed = True
				in_new_contributors = False
				continue

			if line.strip() == "## New Contributors":
				in_new_contributors = True
				in_whats_changed = False
				continue

			if line.startswith("**Full Changelog**"):
				full_changelog = line.strip()
				in_new_contributors = False
				in_whats_changed = False
				continue

			if in_new_contributors:
				new_contributors.append(line.strip())
				continue

			if in_whats_changed:
				release_notes_line = ReleaseNotesLine(line)
				release_notes_line.parse_line()
				whats_changed.append(release_notes_line)
				continue

		return cls(whats_changed, new_contributors, full_changelog)

	def serialize(self) -> str:
		notes = "## What's Changed:"
		for line in self.whats_changed:
			notes += f"\n{line}"

		if self.new_contributors:
			notes += "\n\n## New Contributors:"
			for contributor_line in self.new_contributors:
				notes += f"\n{contributor_line}"

		if self.full_changelog:
			notes += "\n\n"
			notes += self.full_changelog

		return notes
