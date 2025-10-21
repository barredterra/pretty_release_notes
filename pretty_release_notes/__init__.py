"""Pretty Release Notes - Transform GitHub release notes with AI."""

# Public API exports for library usage
from .api import ReleaseNotesBuilder, ReleaseNotesClient
from .core.config import (
	DatabaseConfig,
	FilterConfig,
	GitHubConfig,
	OpenAIConfig,
	ReleaseNotesConfig,
)
from .core.interfaces import (
	CompositeProgressReporter,
	NullProgressReporter,
	ProgressEvent,
	ProgressReporter,
)

__version__ = "1.0.0"

__all__ = [
	# Client classes
	"ReleaseNotesBuilder",
	"ReleaseNotesClient",
	# Configuration
	"ReleaseNotesConfig",
	"GitHubConfig",
	"OpenAIConfig",
	"DatabaseConfig",
	"FilterConfig",
	# Progress reporting
	"ProgressReporter",
	"ProgressEvent",
	"NullProgressReporter",
	"CompositeProgressReporter",
]
