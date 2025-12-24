from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pull_request import PullRequest
from .release_notes_line import ReleaseNotesLine

if TYPE_CHECKING:
	from ..core.config import GroupingConfig


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
		pr_changes = [line.change for line in self.lines if isinstance(line.change, PullRequest)]
		if not pr_changes:
			return

		# Limit concurrency to avoid overwhelming DNS/HTTP clients
		max_workers = min(10, len(pr_changes))
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			futures = [executor.submit(pr.set_reviewers) for pr in pr_changes]
			for future in futures:
				# Propagate exceptions if any reviewer loading fails
				future.result()

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
		grouping: "GroupingConfig | None" = None,
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

		# Build output - either grouped or flat
		if grouping and grouping.group_by_type:
			# Group lines by type
			grouped_lines: dict[str, list[ReleaseNotesLine]] = {}
			other_lines: list[ReleaseNotesLine] = []

			for line in self.lines:
				# Skip filtered lines
				if line.change and (
					is_exluded_type(line.change)
					or has_excluded_label(line.change)
					or is_reverted_or_revert(line.change)
				):
					continue

				# Group by conventional type
				if line.change and line.change.conventional_type:
					type_key = line.change.conventional_type
					if type_key not in grouped_lines:
						grouped_lines[type_key] = []
					grouped_lines[type_key].append(line)
				elif line.change:  # Has change but no type
					other_lines.append(line)
				# Skip lines without changes (headers, empty lines)

			# Build grouped output
			sections = []

			# Add sections in a consistent order
			type_order = ["feat", "fix", "perf", "docs", "refactor", "test", "build", "ci", "chore", "style", "revert"]

			# Add typed sections
			for type_key in type_order:
				if type_key in grouped_lines and grouped_lines[type_key]:
					heading = grouping.get_heading(type_key)
					sections.append(f"## {heading}")
					for line in grouped_lines[type_key]:
						sections.append(str(line))
					sections.append("")  # Empty line after section

			# Add any types not in the standard order
			for type_key, lines_list in grouped_lines.items():
				if type_key not in type_order and lines_list:
					heading = grouping.get_heading(type_key)
					sections.append(f"## {heading}")
					for line in lines_list:
						sections.append(str(line))
					sections.append("")

			# Add other changes section if needed
			if other_lines:
				sections.append(f"## {grouping.other_heading}")
				for line in other_lines:
					sections.append(str(line))
				sections.append("")

			# Join sections, removing trailing empty line
			lines = "\n".join(sections)
		else:
			# Original flat list logic
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
			disclaimer = f"""
				For these release notes, we used an LLM ({model_name}) to review and summarise
				the code changes, along with the associated issue and PR descriptions. It may
				contain typical errors and inaccuracies. You can read the prompt
				[here](https://github.com/barredterra/pretty_release_notes).
			"""
			disclaimer = " ".join(line.strip() for line in disclaimer.splitlines())
			lines += f"""\n\n<details>
<summary>AI content</summary>

{disclaimer}

</details>"""

		return lines
