"""Tests for thread-safe database access."""

import sys
import threading
from pathlib import Path

import pytest

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SQLiteDatabase
from models import Repository


class TestSQLiteDatabaseThreadSafety:
	"""Test thread-safety of SQLiteDatabase."""

	@pytest.fixture
	def temp_db(self, tmp_path):
		"""Create a temporary database for testing."""
		db_path = tmp_path / "test.sqlite"
		db = SQLiteDatabase(db_path)
		yield db
		# Cleanup handled by tmp_path fixture

	@pytest.fixture
	def test_repo(self):
		"""Create a test repository."""
		return Repository(
			owner="test-owner",
			name="test-repo",
			url="https://api.github.com/repos/test-owner/test-repo",
			html_url="https://github.com/test-owner/test-repo",
		)

	def test_concurrent_writes_no_conflicts(self, temp_db, test_repo):
		"""Test that concurrent writes don't cause conflicts."""
		num_threads = 10
		writes_per_thread = 5
		errors = []

		def write_task(thread_id):
			try:
				for i in range(writes_per_thread):
					pr_no = f"pr-{thread_id}-{i}"
					sentence = f"Sentence from thread {thread_id}, write {i}"
					temp_db.store_sentence(test_repo, pr_no, sentence)
			except Exception as e:
				errors.append(e)

		threads = []
		for i in range(num_threads):
			thread = threading.Thread(target=write_task, args=(i,))
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

		assert len(errors) == 0, f"Errors occurred: {errors}"

		# Verify all writes succeeded
		for thread_id in range(num_threads):
			for i in range(writes_per_thread):
				pr_no = f"pr-{thread_id}-{i}"
				result = temp_db.get_sentence(test_repo, pr_no)
				assert result == f"Sentence from thread {thread_id}, write {i}"

	def test_concurrent_reads_no_conflicts(self, temp_db, test_repo):
		"""Test that concurrent reads work correctly."""
		# Pre-populate database
		for i in range(10):
			temp_db.store_sentence(test_repo, f"pr-{i}", f"Sentence {i}")

		num_threads = 20
		results = {}
		errors = []
		lock = threading.Lock()

		def read_task(thread_id):
			try:
				thread_results = []
				for i in range(10):
					sentence = temp_db.get_sentence(test_repo, f"pr-{i}")
					thread_results.append(sentence)

				with lock:
					results[thread_id] = thread_results
			except Exception as e:
				errors.append(e)

		threads = []
		for i in range(num_threads):
			thread = threading.Thread(target=read_task, args=(i,))
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

		assert len(errors) == 0, f"Errors occurred: {errors}"
		assert len(results) == num_threads

		# Verify all threads got the same data
		expected = [f"Sentence {i}" for i in range(10)]
		for thread_id, thread_results in results.items():
			assert thread_results == expected

	def test_mixed_read_write_operations(self, temp_db, test_repo):
		"""Test that mixed read/write operations are thread-safe."""
		num_threads = 10
		operations_per_thread = 20
		errors = []

		def mixed_task(thread_id):
			try:
				for i in range(operations_per_thread):
					if i % 2 == 0:
						# Write
						pr_no = f"pr-{thread_id}-{i}"
						sentence = f"Sentence from thread {thread_id}, op {i}"
						temp_db.store_sentence(test_repo, pr_no, sentence)
					else:
						# Read
						pr_no = f"pr-{thread_id}-{i - 1}"
						temp_db.get_sentence(test_repo, pr_no)
			except Exception as e:
				errors.append(e)

		threads = []
		for i in range(num_threads):
			thread = threading.Thread(target=mixed_task, args=(i,))
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

		assert len(errors) == 0, f"Errors occurred: {errors}"

	def test_thread_local_connections(self, temp_db):
		"""Test that each thread gets its own connection."""
		connections = {}
		lock = threading.Lock()

		def get_connection(thread_id):
			conn = temp_db.connection
			with lock:
				connections[thread_id] = id(conn)

		threads = []
		for i in range(5):
			thread = threading.Thread(target=get_connection, args=(i,))
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

		# Each thread should have a different connection
		connection_ids = list(connections.values())
		assert len(set(connection_ids)) == 5

	def test_transaction_rollback_on_error(self, temp_db, test_repo):
		"""Test that transactions rollback on error."""
		# Store initial value
		temp_db.store_sentence(test_repo, "pr-1", "Initial sentence")

		# Try to do something that will fail in a transaction
		try:
			with temp_db.transaction():
				temp_db.cursor.execute(
					"UPDATE sentences SET sentence = ? WHERE owner = ? AND repo = ? AND pr_no = ?",
					("Updated sentence", test_repo.owner, test_repo.name, "pr-1"),
				)
				# Intentionally cause an error
				raise ValueError("Simulated error")
		except ValueError:
			pass

		# Original value should still be there (transaction rolled back)
		result = temp_db.get_sentence(test_repo, "pr-1")
		assert result == "Initial sentence"

	def test_no_deadlocks_under_load(self, temp_db, test_repo):
		"""Test that no deadlocks occur under high load."""
		num_threads = 20
		operations_per_thread = 50
		errors = []
		completed = {"count": 0}
		lock = threading.Lock()

		def load_task(thread_id):
			try:
				for i in range(operations_per_thread):
					pr_no = f"pr-{thread_id % 5}"  # Create contention
					sentence = f"Thread {thread_id}, op {i}"

					# Mix of operations
					if i % 3 == 0:
						temp_db.store_sentence(test_repo, pr_no, sentence)
					elif i % 3 == 1:
						temp_db.get_sentence(test_repo, pr_no)
					else:
						temp_db.delete_sentence(test_repo, pr_no)

				with lock:
					completed["count"] += 1
			except Exception as e:
				errors.append((thread_id, e))

		threads = []
		for i in range(num_threads):
			thread = threading.Thread(target=load_task, args=(i,))
			threads.append(thread)
			thread.start()

		# Wait with timeout to detect deadlocks
		for thread in threads:
			thread.join(timeout=30)

		# Check all threads completed (with errors printed for debugging)
		if errors:
			print(f"\nErrors encountered: {len(errors)}")
			for i, (thread_id, error) in enumerate(errors[:5]):  # Print first 5 errors
				print(f"  Thread {thread_id}: {error}")
		assert completed["count"] + len(errors) == num_threads, (
			f"Only {completed['count'] + len(errors)}/{num_threads} threads completed"
		)
		# It's OK if some errors occurred due to database conflicts (INSERT of existing keys)
		# The important thing is no deadlocks

	def test_database_integrity_after_concurrent_access(self, temp_db, test_repo):
		"""Test that database maintains integrity after concurrent access."""
		num_threads = 10
		writes_per_thread = 10

		def write_task(thread_id):
			for i in range(writes_per_thread):
				pr_no = f"pr-{thread_id}-{i}"
				sentence = f"Thread {thread_id}, write {i}"
				temp_db.store_sentence(test_repo, pr_no, sentence)

		threads = []
		for i in range(num_threads):
			thread = threading.Thread(target=write_task, args=(i,))
			threads.append(thread)
			thread.start()

		for thread in threads:
			thread.join()

		# Verify database integrity
		conn = temp_db.connection
		cursor = conn.cursor()
		cursor.execute("SELECT COUNT(*) FROM sentences")
		count = cursor.fetchone()[0]

		expected_count = num_threads * writes_per_thread
		assert count == expected_count, f"Expected {expected_count} rows, got {count}"

		# Verify no duplicate entries
		cursor.execute("SELECT COUNT(DISTINCT pr_no) FROM sentences")
		unique_count = cursor.fetchone()[0]
		assert unique_count == expected_count
