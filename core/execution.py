"""Execution strategies for parallel processing."""

import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


class ExecutionStrategy(ABC):
	"""Abstract strategy for parallel execution."""

	@abstractmethod
	def execute_parallel(
		self,
		tasks: list[Callable[[], Any]],
	) -> list[Any]:
		"""Execute tasks in parallel and return results."""
		pass


class ThreadingStrategy(ExecutionStrategy):
	"""Original threading implementation for backward compatibility."""

	def execute_parallel(
		self,
		tasks: list[Callable[[], Any]],
	) -> list[Any]:
		threads = []
		results = [None] * len(tasks)

		def run_task(index: int, task: Callable[[], Any]):
			results[index] = task()

		for i, task in enumerate(tasks):
			thread = threading.Thread(target=run_task, args=(i, task))
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

		return results


class ThreadPoolStrategy(ExecutionStrategy):
	"""Thread pool implementation for better resource management."""

	def __init__(self, max_workers: int = 10):
		self.max_workers = max_workers

	def execute_parallel(
		self,
		tasks: list[Callable[[], Any]],
	) -> list[Any]:
		if not tasks:
			return []

		results = []
		with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
			futures = [executor.submit(task) for task in tasks]
			for future in as_completed(futures):
				results.append(future.result())
		return results


class SequentialStrategy(ExecutionStrategy):
	"""Sequential execution for debugging or environments without threading."""

	def execute_parallel(
		self,
		tasks: list[Callable[[], Any]],
	) -> list[Any]:
		return [task() for task in tasks]
