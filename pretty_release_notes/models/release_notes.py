import threading
from dataclasses import dataclass

from .release_notes_line import ReleaseNotesLine


@dataclass
class ReleaseNotes:
	"""Parse release notes into structured data."""

	lines: list[ReleaseNotesLine]

	@classmethod
	def from_string(cls, release_notes: str) -> "ReleaseNotes":
		return cls(lines=[ReleaseNotesLine.from_string(line) for line in release_notes.split("\n")])

	@property
	def authors(self) -> set[str]:
		return {line.change.get_author() for line in self.lines if line.change}

	def load_reviewers(self) -> None:
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

	def _get_reverted_pr_numbers(self) -> set[str]:
		"""Get all PR numbers that have been reverted in this release.

		Returns a set of PR numbers (as strings) that are reverted by other PRs
		in this release.
		"""
		# First, collect all PR numbers in this release
		pr_numbers_in_release = set()
		for line in self.lines:
			if line.change and hasattr(line.change, "id"):
				pr_numbers_in_release.add(str(line.change.id))

		# Now find which ones are reverted
		reverted_numbers = set()
		for line in self.lines:
			if (
				line.change
				and hasattr(line.change, "is_revert")
				and hasattr(line.change, "reverted_pr_number")
				and line.change.is_revert
			):
				reverted_num = line.change.reverted_pr_number
				# Only mark as reverted if the original PR is also in this release
				if reverted_num and reverted_num in pr_numbers_in_release:
					reverted_numbers.add(reverted_num)

		return reverted_numbers

	def serialize(
		self,
		exclude_change_types: set[str] | None = None,
		exclude_change_labels: set[str] | None = None,
		exclude_authors: set[str] | None = None,
		model_name: str | None = None,
	) -> str:
		def is_exluded_type(change):
			return (
				change.conventional_type and exclude_change_types and change.conventional_type in exclude_change_types
			)

		def has_excluded_label(change):
			return change.labels and exclude_change_labels and change.labels & exclude_change_labels

		# Build a set of PR numbers that should be excluded due to reverts
		reverted_pr_numbers = self._get_reverted_pr_numbers()

		def is_reverted_or_revert(change):
			"""Check if this change is either a revert or has been reverted."""
			if not hasattr(change, "is_revert"):
				return False

			# If this PR is a revert and the original is in this release, exclude both
			if change.is_revert and change.reverted_pr_number in reverted_pr_numbers:
				return True

			# If this PR has been reverted in this release, exclude it
			if str(change.id) in reverted_pr_numbers:
				return True

			return False

		if exclude_authors is None:
			exclude_authors = set()

		lines = "\n".join(
			str(line)
			for line in self.lines
			if not line.change
			or (
				not is_exluded_type(line.change)
				and not has_excluded_label(line.change)
				and not is_reverted_or_revert(line.change)
			)
		)

		authors_string = ", ".join(f"@{author}" for author in self.authors if author not in exclude_authors)

		reviewers_string = ", ".join(
			f"@{reviewer}" for reviewer in self.get_reviewers() if reviewer not in exclude_authors
		)

		if authors_string:
			lines += f"\n**Authors**: {authors_string}"
		if reviewers_string:
			lines += f"\n**Reviewers**: {reviewers_string}"

		if model_name:
			lines += f"""\n\n<details>
<summary>AI content</summary>

For these release notes, we used an LLM ({model_name}) to review and summarise
the code changes, along with the associated issue and PR descriptions. It may
contain typical errors and inaccuracies. You can read the prompt
[here](https://github.com/barredterra/pretty_release_notes).

</details>"""

		return lines
