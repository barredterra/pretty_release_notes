"""CLI adapter for progress reporting."""

from ..core.interfaces import ProgressEvent, ProgressReporter
from ..ui import CLI


class CLIProgressReporter(ProgressReporter):
	"""Adapt ProgressReporter interface to existing CLI class."""

	def __init__(self, cli: CLI):
		self.cli = cli

	def report(self, event: ProgressEvent) -> None:
		"""Route progress events to appropriate CLI methods."""
		if event.type == "markdown":
			self.cli.show_markdown_text(event.message)
		elif event.type == "success":
			self.cli.show_success(event.message)
		elif event.type == "error":
			self.cli.show_error(event.message)
		elif event.type == "info":
			self.cli.show_markdown_text(event.message)
		elif event.type == "release_notes":
			heading = event.metadata.get("heading", "Release Notes") if event.metadata else "Release Notes"
			self.cli.show_release_notes(heading, event.message)
