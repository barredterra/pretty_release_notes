from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProgressEvent:
	type: str  # "info", "success", "error", "markdown"
	message: str
	metadata: dict[str, Any] | None = None


class ProgressReporter(ABC):
	@abstractmethod
	def report(self, event: ProgressEvent) -> None:
		"""Report a progress event."""
		pass


class NullProgressReporter(ProgressReporter):
	"""No-op reporter for library usage."""

	def report(self, event: ProgressEvent) -> None:
		pass


class CompositeProgressReporter(ProgressReporter):
	"""Combine multiple reporters."""

	def __init__(self, reporters: list[ProgressReporter]):
		self.reporters = reporters

	def report(self, event: ProgressEvent) -> None:
		for reporter in self.reporters:
			reporter.report(event)
