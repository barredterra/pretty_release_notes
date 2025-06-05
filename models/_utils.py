import re

CONVENTIONAL_TYPE_AND_SCOPE = re.compile(r"^([a-zA-Z]+)(?:\(([^)]+)\))?:\s+(.+)")


def get_conventional_type(msg: str) -> str | None:
	"""Extract the conventional type from a message.

	Examples:
	'feat(regional): Address Template for Germany & Switzerland' -> 'feat'
	'Revert "perf: timeout while renaming cost center"' -> None
	"""
	match = CONVENTIONAL_TYPE_AND_SCOPE.search(msg)
	return match.group(1) if match else None
