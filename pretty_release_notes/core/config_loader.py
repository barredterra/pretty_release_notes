import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from .config import (
	DatabaseConfig,
	FilterConfig,
	GitHubConfig,
	GroupingConfig,
	OpenAIConfig,
	ReleaseNotesConfig,
	_get_default_prompt_path,
)


class ConfigLoader(ABC):
	@abstractmethod
	def load(self) -> ReleaseNotesConfig:
		"""Load configuration from source."""
		pass


class DictConfigLoader(ConfigLoader):
	"""Load from dictionary (for programmatic usage)."""

	def __init__(self, config_dict: dict[str, Any]):
		self.config_dict = config_dict

	def load(self) -> ReleaseNotesConfig:
		return ReleaseNotesConfig(
			github=GitHubConfig(
				token=self.config_dict["github_token"],
				owner=self.config_dict.get("github_owner"),
			),
			openai=OpenAIConfig(
				api_key=self.config_dict["openai_api_key"],
				model=self.config_dict.get("openai_model", "gpt-4.1"),
				max_patch_size=self.config_dict.get("max_patch_size", 10000),
			),
			database=DatabaseConfig(
				type=self.config_dict.get("db_type", "sqlite"),
				name=self.config_dict.get("db_name", "stored_lines"),
				enabled=self.config_dict.get("use_db", True),
			),
			filters=FilterConfig(
				exclude_change_types=set(self.config_dict.get("exclude_types", [])),
				exclude_change_labels=set(self.config_dict.get("exclude_labels", [])),
				exclude_authors=set(self.config_dict.get("exclude_authors", [])),
			),
			grouping=GroupingConfig(
				group_by_type=self.config_dict.get("group_by_type", False),
				**(
					{}
					if "type_headings" not in self.config_dict
					else {"type_headings": self.config_dict["type_headings"]}
				),
				**(
					{}
					if "other_heading" not in self.config_dict
					else {"other_heading": self.config_dict["other_heading"]}
				),
			),
			prompt_path=Path(self.config_dict["prompt_path"])
			if "prompt_path" in self.config_dict
			else _get_default_prompt_path(),
			force_use_commits=self.config_dict.get("force_use_commits", False),
		)


class EnvConfigLoader(ConfigLoader):
	"""Load from .env file (backward compatibility)."""

	def __init__(self, env_path: str = ".env"):
		self.env_path = env_path

	def load(self) -> ReleaseNotesConfig:
		config = dotenv_values(self.env_path)

		# Required fields - will raise KeyError if missing
		github_token = config["GH_TOKEN"]
		openai_key = config["OPENAI_API_KEY"]

		# Ensure github_token and openai_key are not None
		if github_token is None:
			raise ValueError("GH_TOKEN is required in .env file")
		if openai_key is None:
			raise ValueError("OPENAI_API_KEY is required in .env file")

		return ReleaseNotesConfig(
			github=GitHubConfig(token=github_token, owner=config.get("DEFAULT_OWNER")),
			openai=OpenAIConfig(
				api_key=openai_key,
				model=config.get("OPENAI_MODEL") or "gpt-4.1",
				max_patch_size=int(config.get("MAX_PATCH_SIZE") or "10000"),
			),
			database=DatabaseConfig(
				type=config.get("DB_TYPE") or "sqlite",
				name=config.get("DB_NAME") or "stored_lines",
				enabled=True,
			),
			filters=FilterConfig(
				exclude_change_types=self._parse_set(config.get("EXCLUDE_PR_TYPES") or ""),
				exclude_change_labels=self._parse_set(config.get("EXCLUDE_PR_LABELS") or ""),
				exclude_authors=self._parse_set(config.get("EXCLUDE_AUTHORS") or ""),
			),
			grouping=GroupingConfig(
				group_by_type=(config.get("GROUP_BY_TYPE") or "false").lower() == "true",
			),
			prompt_path=(
				Path(config["PROMPT_PATH"])
				if "PROMPT_PATH" in config and config["PROMPT_PATH"] is not None
				else _get_default_prompt_path()
			),
			force_use_commits=(config.get("FORCE_USE_COMMITS") or "false").lower() == "true",
		)

	def _parse_set(self, value: str) -> set[str]:
		return set(value.split(",")) if value else set()


class TomlConfigLoader(ConfigLoader):
	"""Load from TOML file (default config format)."""

	DEFAULT_CONFIG_PATH = Path.home() / ".pretty-release-notes" / "config.toml"

	def __init__(self, config_path: Path | str | None = None):
		"""Initialize TOML config loader.

		Args:
			config_path: Path to config file. If None, uses DEFAULT_CONFIG_PATH.
		"""
		if config_path is None:
			self.config_path = self.DEFAULT_CONFIG_PATH
		else:
			self.config_path = Path(config_path)

	def load(self) -> ReleaseNotesConfig:
		"""Load configuration from TOML file.

		Raises:
			FileNotFoundError: If config file doesn't exist
			ValueError: If required fields are missing or invalid
		"""
		if not self.config_path.exists():
			raise FileNotFoundError(
				f"Config file not found at {self.config_path}. "
				f"Create it with the required fields or use --config-path to specify a different location."
			)

		with open(self.config_path, "rb") as f:
			config = tomllib.load(f)

		# Extract nested sections with defaults
		github_config = config.get("github", {})
		openai_config = config.get("openai", {})
		database_config = config.get("database", {})
		filters_config = config.get("filters", {})
		grouping_config = config.get("grouping", {})

		# Required fields
		github_token = github_config.get("token")
		openai_key = openai_config.get("api_key")

		if not github_token:
			raise ValueError("github.token is required in config file")
		if not openai_key:
			raise ValueError("openai.api_key is required in config file")

		return ReleaseNotesConfig(
			github=GitHubConfig(
				token=github_token,
				owner=github_config.get("owner"),
			),
			openai=OpenAIConfig(
				api_key=openai_key,
				model=openai_config.get("model", "gpt-4.1"),
				max_patch_size=openai_config.get("max_patch_size", 10000),
			),
			database=DatabaseConfig(
				type=database_config.get("type", "sqlite"),
				name=database_config.get("name", "stored_lines"),
				enabled=database_config.get("enabled", True),
			),
			filters=FilterConfig(
				exclude_change_types=set(filters_config.get("exclude_change_types", [])),
				exclude_change_labels=set(filters_config.get("exclude_change_labels", [])),
				exclude_authors=set(filters_config.get("exclude_authors", [])),
			),
			grouping=GroupingConfig(
				group_by_type=grouping_config.get("group_by_type", False),
				**(
					{}
					if "type_headings" not in grouping_config
					else {"type_headings": grouping_config["type_headings"]}
				),
				**(
					{}
					if "other_heading" not in grouping_config
					else {"other_heading": grouping_config["other_heading"]}
				),
			),
			prompt_path=Path(config["prompt_path"]) if "prompt_path" in config else _get_default_prompt_path(),
			force_use_commits=config.get("force_use_commits", False),
		)
