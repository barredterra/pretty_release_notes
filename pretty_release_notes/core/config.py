from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitHubConfig:
	token: str
	owner: str | None = None

	def __post_init__(self):
		if not self.token:
			raise ValueError("GitHub token is required")


@dataclass
class OpenAIConfig:
	api_key: str
	model: str = "gpt-4.1"
	max_patch_size: int = 10000

	def __post_init__(self):
		if not self.api_key:
			raise ValueError("OpenAI API key is required")


@dataclass
class DatabaseConfig:
	"""Database configuration for caching release note summaries.

	Attributes:
		type: Database backend type ("csv" or "sqlite")
		name: Database filename (without extension). If relative, stores in ~/.pretty-release-notes/
			If absolute path, stores at that exact location.
		enabled: Whether to use database caching
	"""

	type: str = "sqlite"
	name: str = "stored_lines"
	enabled: bool = True

	def __post_init__(self):
		if self.type not in ("csv", "sqlite"):
			raise ValueError(f"Invalid database type: {self.type}")


@dataclass
class FilterConfig:
	exclude_change_types: set[str] = field(default_factory=set)
	exclude_change_labels: set[str] = field(default_factory=set)
	exclude_authors: set[str] = field(default_factory=set)


@dataclass
class GroupingConfig:
	"""Configuration for grouping release notes output."""

	group_by_type: bool = False
	type_headings: dict[str, str] = field(
		default_factory=lambda: {
			"feat": "Features",
			"fix": "Bug Fixes",
			"perf": "Performance Improvements",
			"docs": "Documentation",
			"refactor": "Code Refactoring",
			"test": "Tests",
			"build": "Build System",
			"ci": "CI/CD",
			"chore": "Chores",
			"style": "Style",
			"revert": "Reverts",
		}
	)
	other_heading: str = "Other Changes"

	def get_heading(self, type_name: str | None) -> str:
		"""Get the section heading for a given type."""
		if not type_name:
			return self.other_heading
		return self.type_headings.get(type_name, self.other_heading)


def _get_default_prompt_path() -> Path:
	"""Get the default prompt.txt path from the package directory."""
	# Get the directory where this config.py file is located
	package_dir = Path(__file__).parent.parent
	return package_dir / "prompt.txt"


@dataclass
class ReleaseNotesConfig:
	github: GitHubConfig
	openai: OpenAIConfig
	database: DatabaseConfig = field(default_factory=DatabaseConfig)
	filters: FilterConfig = field(default_factory=FilterConfig)
	grouping: GroupingConfig = field(default_factory=GroupingConfig)
	prompt_path: Path = field(default_factory=_get_default_prompt_path)
	force_use_commits: bool = False
