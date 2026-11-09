from typing import TYPE_CHECKING

from ._utils import CONVENTIONAL_TYPE_ORDER
from .release_notes_line import ReleaseNotesLine

if TYPE_CHECKING:
	from ..core.config import GroupingConfig

# An area with more entries than this is collapsed
MAX_EXPANDED_LINES = 3


class AreaSections:
	"""Changes grouped by area, so readers can go to the part of the product they use.

	Breaking changes come first, then the general section, then the areas in configured order.
	Inside an area, changes are grouped by type, and each group is labeled with its type.
	Large areas show each group collapsed, so the reader sees an overview first.
	"""

	def __init__(self, change_lines: list[ReleaseNotesLine], grouping: "GroupingConfig", repo: str):
		self.grouping = grouping
		self.repo = repo
		self.breaking_lines: list[ReleaseNotesLine] = []
		self.lines_by_area: dict[str, list[ReleaseNotesLine]] = {}

		for line in change_lines:
			change = line.change
			assert change, "Only lines with a change can be grouped by area"
			if change.is_breaking:
				self.breaking_lines.append(line)
				continue

			area = grouping.get_area_heading(repo, change.conventional_scope, change.labels)
			self.lines_by_area.setdefault(area, []).append(line)

	def to_markdown(self) -> list[str]:
		sections = []
		if self.breaking_lines:
			sections += [f"## {self.grouping.breaking_changes_heading}", *map(str, self.breaking_lines), ""]

		for area in self._get_area_order():
			if area in self.lines_by_area:
				sections += self._get_area_section(area, self.lines_by_area[area])

		return sections

	def _get_area_order(self) -> list[str]:
		configured_areas = dict.fromkeys(self.grouping.get_area_headings(self.repo).values())
		return [self.grouping.general_heading, *configured_areas]

	def _get_area_section(self, area: str, lines: list[ReleaseNotesLine]) -> list[str]:
		lines_by_type = self._group_by_type(lines)
		collapse = len(lines) > MAX_EXPANDED_LINES

		section = [f"## {area}"]
		for type_heading, type_lines in lines_by_type.items():
			if collapse:
				# GitHub only renders markdown inside <details> with blank lines around it
				section += ["", "<details>", f"<summary>{type_heading} ({len(type_lines)})</summary>", ""]
				section += [*map(str, type_lines), "", "</details>"]
			else:
				section += ["", type_heading, "", *map(str, type_lines)]

		section.append("")
		return section

	def _group_by_type(self, lines: list[ReleaseNotesLine]) -> dict[str, list[ReleaseNotesLine]]:
		"""Group lines by type heading, in the usual type order. Unknown types share the "other" heading."""
		lines_by_type: dict[str, list[ReleaseNotesLine]] = {}
		for line in sorted(lines, key=lambda line: _get_type_rank(line.conventional_type)):
			type_heading = self.grouping.get_heading(line.conventional_type)
			lines_by_type.setdefault(type_heading, []).append(line)

		return lines_by_type


def _get_type_rank(conventional_type: str | None) -> int:
	"""Known types in the usual order, unknown and missing types last."""
	if conventional_type in CONVENTIONAL_TYPE_ORDER:
		return CONVENTIONAL_TYPE_ORDER.index(conventional_type)
	return len(CONVENTIONAL_TYPE_ORDER)
