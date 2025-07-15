import re

CONVENTIONAL_TYPE_AND_SCOPE = re.compile(r"^([a-zA-Z]{2,8})(?:\(([^)]+)\))?:")


def get_conventional_type(msg: str) -> str | None:
	"""Extract the conventional type from a message.

	Examples:
	'feat(regional): Address Template for Germany & Switzerland' -> 'feat'
	'Revert "perf: timeout while renaming cost center"' -> None
	"""
	if not msg or len(msg) < 3:
		return None

	match = CONVENTIONAL_TYPE_AND_SCOPE.match(msg)
	return match.group(1) if match else None
