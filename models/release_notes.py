from dataclasses import dataclass
import threading

from .release_notes_line import ReleaseNotesLine


@dataclass
class ReleaseNotes:
	"""Parse release notes into structured data."""

	lines: list[ReleaseNotesLine]

	@classmethod
	def from_string(cls, release_notes: str) -> "ReleaseNotes":
		return cls(
			lines=[
				ReleaseNotesLine.from_string(line) for line in release_notes.split("\n")
			]
		)

	@property
	def authors(self) -> set[str]:
		return {line.change.get_author() for line in self.lines if line.change}

	def load_reviewers(self) -> set[str]:
		threads = []
		for line in self.lines:
			if not line.change:
				continue

			thread = threading.Thread(target=line.change.set_reviewers)
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

	def get_reviewers(self) -> set[str]:
		reviewers = set()
		for line in self.lines:
			if line.change and line.change.reviewers:
				reviewers.update(line.change.reviewers)
		return reviewers

	def serialize(
		self,
		exclude_change_types: set[str] | None = None,
		exclude_change_labels: set[str] | None = None,
		exclude_authors: set[str] | None = None,
		model_name: str | None = None,
	) -> str:
		def is_exluded_type(change):
			return (
				change.conventional_type
				and exclude_change_types
				and change.conventional_type in exclude_change_types
			)

		def has_excluded_label(change):
			return (
				change.labels
				and exclude_change_labels
				and change.labels & exclude_change_labels
			)

		if exclude_authors is None:
			exclude_authors = set()

		lines = "\n".join(
			str(line)
			for line in self.lines
			if not line.change
			or (
				not is_exluded_type(line.change) and not has_excluded_label(line.change)
			)
		)

		authors_string = ", ".join(
			f"@{author}" for author in self.authors if author not in exclude_authors
		)

		reviewers_string = ", ".join(
			f"@{reviewer}"
			for reviewer in self.get_reviewers()
			if reviewer not in exclude_authors
		)

		if authors_string:
			lines += f"\n**Authors**: {authors_string}"
		if reviewers_string:
			lines += f"\n**Reviewers**: {reviewers_string}"

		if model_name:
			lines += f"""\n\n<details>
<summary>AI content</summary>

For these release notes, we used an LLM ({model_name}) to review and summarise the code changes, along with the associated issue and PR descriptions. It may contain typical errors and inaccuracies. You can read the prompt [here](https://github.com/barredterra/pretty_release_notes).

</details>"""

		return lines
