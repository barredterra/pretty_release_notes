from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

from dotenv import dotenv_values

from .config import (
	DatabaseConfig,
	FilterConfig,
	GitHubConfig,
	OpenAIConfig,
	ReleaseNotesConfig,
)


class ConfigLoader(ABC):
	@abstractmethod
	def load(self) -> ReleaseNotesConfig:
		"""Load configuration from source."""
		pass


class DictConfigLoader(ConfigLoader):
	"""Load from dictionary (for programmatic usage)."""

	def __init__(self, config_dict: Dict[str, Any]):
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
			prompt_path=Path(self.config_dict.get("prompt_path", "prompt.txt")),
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
			prompt_path=Path(config.get("PROMPT_PATH") or "prompt.txt"),
			force_use_commits=(config.get("FORCE_USE_COMMITS") or "false").lower() == "true",
		)

	def _parse_set(self, value: str) -> set[str]:
		return set(value.split(",")) if value else set()
