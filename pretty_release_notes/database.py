import sqlite3
import threading
from contextlib import contextmanager
from csv import DictReader, DictWriter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from .models import Repository


class Database:
	def __init__(self, path: Path):
		self.path = path

	def get_sentence(self, repository: "Repository", pr_no: str) -> str | None:
		pass

	def store_sentence(self, repository: "Repository", pr_no: str, sentence: str) -> None:
		pass

	def delete_sentence(self, repository: "Repository", pr_no: str) -> None:
		pass


class CSVDatabase(Database):
	columns = ["owner", "repo", "pr_no", "sentence"]

	def get_sentence(self, repository: "Repository", pr_no: str) -> str | None:
		if not self.path.exists():
			return None

		with open(self.path) as f:
			reader = DictReader(f, fieldnames=self.columns)
			for row in reader:
				if row["owner"] == repository.owner and row["repo"] == repository.name and row["pr_no"] == pr_no:
					return row["sentence"]

		return None

	def store_sentence(self, repository: "Repository", pr_no: str, sentence: str) -> None:
		write_header = not self.path.exists()
		with open(self.path, "a") as f:
			writer = DictWriter(f, self.columns)

			if write_header:
				writer.writeheader()

			writer.writerow(
				{
					"owner": repository.owner,
					"repo": repository.name,
					"pr_no": pr_no,
					"sentence": sentence,
				}
			)

	def delete_sentence(self, repository: "Repository", pr_no: str) -> None:
		with open(self.path) as f:
			reader = DictReader(f, fieldnames=self.columns)
			rows = [
				row
				for row in reader
				if row["owner"] != repository.owner or row["repo"] != repository.name or row["pr_no"] != pr_no
			]

		with open(self.path, "w") as f:
			writer = DictWriter(f, self.columns)
			writer.writeheader()
			writer.writerows(rows)


class SQLiteDatabase(Database):
	"""Thread-safe SQLite database with thread-local connections."""

	def __init__(self, path: Path):
		self.path = path
		self._lock = threading.Lock()
		self._local = threading.local()

	@property
	def connection(self):
		"""Thread-local database connection."""
		if not hasattr(self._local, "conn"):
			self._local.conn = sqlite3.connect(self.path)
			self._local.cursor = self._local.conn.cursor()
			self._create_table()
		return self._local.conn

	@property
	def cursor(self):
		"""Thread-local cursor."""
		_ = self.connection  # Ensure connection exists
		return self._local.cursor

	@contextmanager
	def transaction(self):
		"""Context manager for transactions with locking."""
		with self._lock:
			try:
				yield self.cursor
				self.connection.commit()
			except Exception:
				self.connection.rollback()
				raise

	def get_sentence(self, repository: "Repository", pr_no: str) -> str | None:
		# Read operations don't need locking, just use thread-local connection
		self.cursor.execute(
			"SELECT sentence FROM sentences WHERE owner = ? AND repo = ? AND pr_no = ?",
			(repository.owner, repository.name, pr_no),
		)
		result = self.cursor.fetchone()
		return result[0] if result else None

	def store_sentence(self, repository: "Repository", pr_no: str, sentence: str) -> None:
		with self.transaction():
			self.cursor.execute(
				"INSERT INTO sentences (owner, repo, pr_no, sentence) VALUES (?, ?, ?, ?)",
				(repository.owner, repository.name, pr_no, sentence),
			)

	def delete_sentence(self, repository: "Repository", pr_no: str) -> None:
		with self.transaction():
			self.cursor.execute(
				"DELETE FROM sentences WHERE owner = ? AND repo = ? AND pr_no = ?",
				(repository.owner, repository.name, pr_no),
			)

	def _create_table(self):
		"""Create table and index if they don't exist."""
		self.cursor.execute("CREATE TABLE IF NOT EXISTS sentences (owner TEXT, repo TEXT, pr_no TEXT, sentence TEXT)")
		self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner_repo_pr_no ON sentences (owner, repo, pr_no)")
		self.connection.commit()


def get_db(db_type: str, db_name: str) -> Database:
	db_path = Path(db_name)

	if db_type == "csv":
		return CSVDatabase(db_path.with_suffix(".csv"))
	elif db_type == "sqlite":
		return SQLiteDatabase(db_path.with_suffix(".sqlite"))
	else:
		raise ValueError(f"Invalid database type: {db_type}")
