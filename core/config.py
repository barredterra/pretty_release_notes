from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class GitHubConfig:
	token: str
	owner: Optional[str] = None

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
class ReleaseNotesConfig:
	github: GitHubConfig
	openai: OpenAIConfig
	database: DatabaseConfig = field(default_factory=DatabaseConfig)
	filters: FilterConfig = field(default_factory=FilterConfig)
	prompt_path: Path = Path("prompt.txt")
	force_use_commits: bool = False
