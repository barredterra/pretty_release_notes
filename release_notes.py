from dataclasses import dataclass
import re

REGEX_PR_URL = re.compile(
	r"https://github.com/[^/]+/[^/]+/pull/(\d+)"
)  # reqex to find PR URL


@dataclass
class ReleaseNotesLine:
	sentence: str
	pr_url: str
	pr_no: str

	def __str__(self):
		return (
			f"""* {self.sentence} ({self.pr_url})"""
			if self.pr_url
			else f"""* {self.sentence}"""
		)


class ReleaseNotes:
	"""Parse release notes into structured data."""

	def __init__(self):
		self.whats_changed: list[ReleaseNotesLine] = []
		self.new_contributors: list[str] = []
		self.full_changelog: str = ""

	def parse(self, release_notes: str) -> None:
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
				self.full_changelog = line.strip()
				self.in_new_contributors = False
				self.in_whats_changed = False
				continue

			if in_new_contributors:
				self.new_contributors.append(line.strip())
				continue

			if in_whats_changed:
				match = REGEX_PR_URL.search(line)
				pr_url = match.group(0) if match else None
				pr_no = match.group(1) if match else None

				if line.startswith("* "):
					line = line[2:]

				line = line.strip()
				line = line.replace(pr_url, "").strip()
				self.whats_changed.append(ReleaseNotesLine(line, pr_url, pr_no))
				continue

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
