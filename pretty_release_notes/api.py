"""High-level API for library usage of pretty_release_notes."""

from pathlib import Path

from .core.config import (
	DatabaseConfig,
	FilterConfig,
	GitHubConfig,
	OpenAIConfig,
	ReleaseNotesConfig,
)
from .core.interfaces import NullProgressReporter, ProgressReporter
from .generator import ReleaseNotesGenerator


class ReleaseNotesClient:
	"""High-level client for generating release notes."""

	def __init__(
		self,
		config: ReleaseNotesConfig,
		progress_reporter: ProgressReporter | None = None,
	):
		self.config = config
		self.progress_reporter = progress_reporter or NullProgressReporter()

	def generate_release_notes(
		self,
		owner: str,
		repo: str,
		tag: str,
	) -> str:
		"""Generate release notes for a repository and tag.

		Args:
			owner: Repository owner
			repo: Repository name
			tag: Git tag for the release

		Returns:
			Formatted release notes as markdown
		"""
		generator = ReleaseNotesGenerator(self.config, self.progress_reporter)
		generator.initialize_repository(owner, repo)
		return generator.generate(tag)

	def update_github_release(
		self,
		owner: str,
		repo: str,
		tag: str,
		notes: str,
	) -> None:
		"""Update release notes on GitHub.

		Args:
			owner: Repository owner
			repo: Repository name
			tag: Git tag for the release
			notes: New release notes content
		"""
		generator = ReleaseNotesGenerator(self.config, self.progress_reporter)
		generator.initialize_repository(owner, repo)
		generator.update_on_github(notes, tag)


class ReleaseNotesBuilder:
	"""Builder pattern for constructing ReleaseNotesClient."""

	def __init__(self):
		self._github_token = None
		self._openai_key = None
		self._openai_model = "gpt-4.1"
		self._max_patch_size = 10000
		self._db_type = "sqlite"
		self._db_name = "stored_lines"
		self._db_enabled = True
		self._exclude_types = set()
		self._exclude_labels = set()
		self._exclude_authors = set()
		self._prompt_path = Path("prompt.txt")
		self._force_use_commits = False
		self._progress_reporter = None

	def with_github_token(self, token: str) -> "ReleaseNotesBuilder":
		"""Set GitHub authentication token."""
		self._github_token = token
		return self

	def with_openai(self, api_key: str, model: str = "gpt-4.1", max_patch_size: int = 10000) -> "ReleaseNotesBuilder":
		"""Set OpenAI configuration."""
		self._openai_key = api_key
		self._openai_model = model
		self._max_patch_size = max_patch_size
		return self

	def with_database(
		self, db_type: str = "sqlite", db_name: str = "stored_lines", enabled: bool = True
	) -> "ReleaseNotesBuilder":
		"""Configure database for caching generated summaries."""
		self._db_type = db_type
		self._db_name = db_name
		self._db_enabled = enabled
		return self

	def with_filters(
		self,
		exclude_types: set[str] | None = None,
		exclude_labels: set[str] | None = None,
		exclude_authors: set[str] | None = None,
	) -> "ReleaseNotesBuilder":
		"""Set filters for excluding specific types, labels, or authors."""
		if exclude_types:
			self._exclude_types = exclude_types
		if exclude_labels:
			self._exclude_labels = exclude_labels
		if exclude_authors:
			self._exclude_authors = exclude_authors
		return self

	def with_prompt_file(self, path: Path) -> "ReleaseNotesBuilder":
		"""Set custom prompt file path."""
		self._prompt_path = path
		return self

	def with_force_commits(self, force: bool = True) -> "ReleaseNotesBuilder":
		"""Force using commits even when PRs are available."""
		self._force_use_commits = force
		return self

	def with_progress_reporter(self, reporter: ProgressReporter) -> "ReleaseNotesBuilder":
		"""Set custom progress reporter."""
		self._progress_reporter = reporter
		return self

	def build(self) -> ReleaseNotesClient:
		"""Build the client with configured options.

		Raises:
			ValueError: If required configuration is missing
		"""
		if not self._github_token:
			raise ValueError("GitHub token is required")
		if not self._openai_key:
			raise ValueError("OpenAI API key is required")

		config = ReleaseNotesConfig(
			github=GitHubConfig(token=self._github_token),
			openai=OpenAIConfig(
				api_key=self._openai_key,
				model=self._openai_model,
				max_patch_size=self._max_patch_size,
			),
			database=DatabaseConfig(
				type=self._db_type,
				name=self._db_name,
				enabled=self._db_enabled,
			),
			filters=FilterConfig(
				exclude_change_types=self._exclude_types,
				exclude_change_labels=self._exclude_labels,
				exclude_authors=self._exclude_authors,
			),
			prompt_path=self._prompt_path,
			force_use_commits=self._force_use_commits,
		)

		return ReleaseNotesClient(config, self._progress_reporter)
