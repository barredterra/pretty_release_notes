import re

CONVENTIONAL_TYPE_AND_SCOPE = re.compile(r"^([a-zA-Z]{2,8})(?:\(([^)]+)\))?!?:")
BREAKING_CHANGE_PATTERN = re.compile(r"^[a-zA-Z]{2,8}(?:\([^)]+\))?!:")


def get_conventional_type(msg: str) -> str | None:
	"""Extract the conventional type from a message.

	Examples:
	'feat(regional): Address Template for Germany & Switzerland' -> 'feat'
	'Revert "perf: timeout while renaming cost center"' -> None
	'fix!: breaking change' -> 'fix'
	"""
	if not msg:
		return None

	# Strip leading/trailing whitespace
	msg = msg.strip()

	if len(msg) < 3:
		return None

	match = CONVENTIONAL_TYPE_AND_SCOPE.match(msg)
	return match.group(1).lower() if match else None


def is_breaking_change(msg: str) -> bool:
	"""Check if a message indicates a breaking change.

	Breaking changes are indicated by an exclamation mark (!) after the type/scope
	and before the colon, following the Conventional Commits specification.

	Examples:
	'feat!: breaking feature' -> True
	'fix(api)!: breaking fix' -> True
	'feat: regular feature' -> False
	"""
	if not msg:
		return False

	# Strip leading/trailing whitespace
	msg = msg.strip()

	# Check for the ! indicator before the colon
	# Pattern: type(scope)!: or type!:
	return bool(BREAKING_CHANGE_PATTERN.match(msg))
