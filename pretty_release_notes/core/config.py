from dataclasses import dataclass, field
from pathlib import Path

from ..openai_client import DEFAULT_MODEL, ReasoningEffort, normalize_reasoning_effort


@dataclass
class GitHubConfig:
	token: str
	owner: str | None = None

	def __post_init__(self):
		if not self.token:
			raise ValueError("GitHub token is required")


@dataclass
class LLMConfig:
	api_key: str
	model: str = DEFAULT_MODEL
	max_patch_size: int = 10000
	reasoning_effort: ReasoningEffort | None = None

	def __post_init__(self):
		if not self.api_key:
			raise ValueError("LLM API key is required")
		self.reasoning_effort = normalize_reasoning_effort(self.reasoning_effort)


OpenAIConfig = LLMConfig


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
	breaking_changes_heading: str = "Breaking Changes"

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


@dataclass(init=False)
class ReleaseNotesConfig:
	github: GitHubConfig
	llm: LLMConfig
	database: DatabaseConfig = field(default_factory=DatabaseConfig)
	filters: FilterConfig = field(default_factory=FilterConfig)
	grouping: GroupingConfig = field(default_factory=GroupingConfig)
	prompt_path: Path = field(default_factory=_get_default_prompt_path)
	force_use_commits: bool = False

	def __init__(
		self,
		github: GitHubConfig,
		llm: LLMConfig | None = None,
		openai: LLMConfig | None = None,
		database: DatabaseConfig | None = None,
		filters: FilterConfig | None = None,
		grouping: GroupingConfig | None = None,
		prompt_path: Path | None = None,
		force_use_commits: bool = False,
	):
		if llm is not None and openai is not None and llm != openai:
			raise ValueError("Pass either llm or openai configuration, not both")

		resolved_llm = llm or openai
		if resolved_llm is None:
			raise ValueError("LLM configuration is required")

		self.github = github
		self.llm = resolved_llm
		self.database = database if database is not None else DatabaseConfig()
		self.filters = filters if filters is not None else FilterConfig()
		self.grouping = grouping if grouping is not None else GroupingConfig()
		self.prompt_path = prompt_path if prompt_path is not None else _get_default_prompt_path()
		self.force_use_commits = force_use_commits

	@property
	def openai(self) -> LLMConfig:
		"""Backward-compatible alias for llm configuration."""
		return self.llm

	@openai.setter
	def openai(self, value: LLMConfig) -> None:
		self.llm = value
