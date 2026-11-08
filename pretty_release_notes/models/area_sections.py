from typing import TYPE_CHECKING

from ._utils import CONVENTIONAL_TYPE_ORDER
from .release_notes_line import ReleaseNotesLine

if TYPE_CHECKING:
	from ..core.config import GroupingConfig


class AreaSections:
	"""Changes grouped by area, so readers can go to the part of the product they use.

	Breaking changes come first, then the general section, then the areas in configured order.
	Inside an area, bug fixes are collapsed. Everything else stays visible.
	"""

	def __init__(self, change_lines: list[ReleaseNotesLine], grouping: "GroupingConfig"):
		self.grouping = grouping
		self.breaking_lines: list[ReleaseNotesLine] = []
		self.lines_by_area: dict[str, list[ReleaseNotesLine]] = {}

		for line in change_lines:
			change = line.change
			assert change, "Only lines with a change can be grouped by area"
			if change.is_breaking:
				self.breaking_lines.append(line)
				continue

			area = grouping.get_area_heading(change.conventional_scope, change.labels)
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
		configured_areas = dict.fromkeys(self.grouping.area_headings.values())
		return [self.grouping.general_heading, *configured_areas]

	def _get_area_section(self, area: str, lines: list[ReleaseNotesLine]) -> list[str]:
		fix_lines = [line for line in lines if line.conventional_type == "fix"]
		visible_lines = sorted(
			(line for line in lines if line.conventional_type != "fix"),
			key=lambda line: _get_type_rank(line.conventional_type),
		)

		section = [f"## {area}", *map(str, visible_lines)]
		if fix_lines:
			fixes_summary = f"{self.grouping.get_heading('fix')} ({len(fix_lines)})"
			# GitHub only renders markdown inside <details> with blank lines around it
			section += ["", "<details>", f"<summary>{fixes_summary}</summary>", ""]
			section += [*map(str, fix_lines), "", "</details>"]

		section.append("")
		return section


def _get_type_rank(conventional_type: str | None) -> int:
	"""Known types in the usual order, unknown and missing types last."""
	if conventional_type in CONVENTIONAL_TYPE_ORDER:
		return CONVENTIONAL_TYPE_ORDER.index(conventional_type)
	return len(CONVENTIONAL_TYPE_ORDER)
