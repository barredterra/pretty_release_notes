"""Tests for execution strategies."""

import sys
import threading
import time
from pathlib import Path

import pytest

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.execution import (
	ExecutionStrategy,
	SequentialStrategy,
	ThreadingStrategy,
	ThreadPoolStrategy,
)


class TestExecutionStrategies:
	"""Test all execution strategy implementations."""

	def test_sequential_strategy_executes_in_order(self):
		"""Test that sequential strategy executes tasks in order."""
		results = []

		def task(value):
			def _task():
				results.append(value)
				return value

			return _task

		strategy = SequentialStrategy()
		tasks = [task(i) for i in range(5)]
		returned_results = strategy.execute_parallel(tasks)

		assert results == [0, 1, 2, 3, 4]
		assert set(returned_results) == {0, 1, 2, 3, 4}

	def test_threading_strategy_executes_all_tasks(self):
		"""Test that threading strategy executes all tasks."""
		counter = {"value": 0}
		lock = threading.Lock()

		def task():
			with lock:
				counter["value"] += 1
			time.sleep(0.01)  # Simulate work
			return counter["value"]

		strategy = ThreadingStrategy()
		tasks = [task for _ in range(10)]
		results = strategy.execute_parallel(tasks)

		assert len(results) == 10
		assert counter["value"] == 10

	def test_thread_pool_strategy_executes_all_tasks(self):
		"""Test that thread pool strategy executes all tasks."""
		counter = {"value": 0}
		lock = threading.Lock()

		def task():
			with lock:
				counter["value"] += 1
			time.sleep(0.01)  # Simulate work
			return counter["value"]

		strategy = ThreadPoolStrategy(max_workers=5)
		tasks = [task for _ in range(10)]
		results = strategy.execute_parallel(tasks)

		assert len(results) == 10
		assert counter["value"] == 10

	def test_thread_pool_with_empty_tasks(self):
		"""Test that thread pool handles empty task list."""
		strategy = ThreadPoolStrategy()
		results = strategy.execute_parallel([])
		assert results == []

	def test_thread_pool_limits_concurrent_workers(self):
		"""Test that thread pool limits concurrent workers."""
		active_workers = {"count": 0, "max": 0}
		lock = threading.Lock()

		def task():
			with lock:
				active_workers["count"] += 1
				if active_workers["count"] > active_workers["max"]:
					active_workers["max"] = active_workers["count"]

			time.sleep(0.1)  # Simulate work

			with lock:
				active_workers["count"] -= 1

			return True

		strategy = ThreadPoolStrategy(max_workers=3)
		tasks = [task for _ in range(10)]
		strategy.execute_parallel(tasks)

		# Max workers should not exceed configured limit
		assert active_workers["max"] <= 3

	def test_strategies_handle_exceptions(self):
		"""Test that strategies handle exceptions in tasks."""

		def failing_task():
			raise ValueError("Task failed")

		def success_task():
			return "success"

		# Sequential strategy should raise exception
		strategy = SequentialStrategy()
		with pytest.raises(ValueError, match="Task failed"):
			strategy.execute_parallel([failing_task])

		# Thread pool should also propagate exception
		strategy = ThreadPoolStrategy()
		with pytest.raises(ValueError, match="Task failed"):
			strategy.execute_parallel([failing_task])

	def test_strategies_return_results(self):
		"""Test that all strategies return task results."""

		def task(value):
			return lambda: value * 2

		values = [1, 2, 3, 4, 5]

		# Sequential
		strategy = SequentialStrategy()
		results = strategy.execute_parallel([task(v) for v in values])
		assert set(results) == {2, 4, 6, 8, 10}

		# Threading
		strategy = ThreadingStrategy()
		results = strategy.execute_parallel([task(v) for v in values])
		assert set(results) == {2, 4, 6, 8, 10}

		# Thread pool
		strategy = ThreadPoolStrategy()
		results = strategy.execute_parallel([task(v) for v in values])
		assert set(results) == {2, 4, 6, 8, 10}

	def test_thread_pool_max_workers_configuration(self):
		"""Test that thread pool max_workers can be configured."""
		strategy = ThreadPoolStrategy(max_workers=20)
		assert strategy.max_workers == 20

		strategy = ThreadPoolStrategy(max_workers=5)
		assert strategy.max_workers == 5

	def test_execution_strategy_is_abstract(self):
		"""Test that ExecutionStrategy cannot be instantiated directly."""
		with pytest.raises(TypeError):
			ExecutionStrategy()  # noqa: E0110


class TestExecutionPerformance:
	"""Test performance characteristics of execution strategies."""

	def test_parallel_faster_than_sequential(self):
		"""Test that parallel execution is faster than sequential for I/O bound tasks."""

		def slow_task():
			time.sleep(0.1)
			return True

		tasks = [slow_task for _ in range(5)]

		# Measure sequential
		start = time.time()
		SequentialStrategy().execute_parallel(tasks)
		sequential_time = time.time() - start

		# Measure parallel (thread pool)
		start = time.time()
		ThreadPoolStrategy(max_workers=5).execute_parallel(tasks)
		parallel_time = time.time() - start

		# Parallel should be significantly faster (at least 2x)
		assert parallel_time < sequential_time / 2


class TestIntegrationWithGenerator:
	"""Test execution strategies work with generator-like patterns."""

	def test_lambda_tasks_with_closure(self):
		"""Test that lambda tasks with closures work correctly."""
		items = [1, 2, 3, 4, 5]
		results = []
		lock = threading.Lock()

		def process_item(item):
			with lock:
				results.append(item * 2)

		# Create tasks with proper closure
		tasks = [lambda item=item: process_item(item) for item in items]

		strategy = ThreadPoolStrategy()
		strategy.execute_parallel(tasks)

		assert set(results) == {2, 4, 6, 8, 10}

	def test_object_mutation_in_parallel(self):
		"""Test that objects can be safely mutated in parallel tasks."""

		class Item:
			def __init__(self, value):
				self.value = value
				self.processed = False

		items = [Item(i) for i in range(10)]

		def process_item(item):
			item.processed = True
			item.value *= 2

		tasks = [lambda item=item: process_item(item) for item in items]

		strategy = ThreadPoolStrategy()
		strategy.execute_parallel(tasks)

		assert all(item.processed for item in items)
		assert [item.value for item in items] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
