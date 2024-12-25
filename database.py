from csv import DictReader, DictWriter
from pathlib import Path
import sqlite3


class Database:
	def __init__(self, path: Path):
		self.path = path

	def get_sentence(self, owner, repo, pr_no) -> str | None:
		pass

	def store_sentence(self, owner, repo, pr_no, line) -> None:
		pass


class CSVDatabase(Database):
	def get_sentence(self, owner, repo, pr_no):
		if not self.path.exists():
			return None

		with open(self.path, "r") as f:
			reader = DictReader(f, fieldnames=["owner", "repo", "pr_no", "line"])
			for row in reader:
				if (
					row["owner"] == owner
					and row["repo"] == repo
					and row["pr_no"] == pr_no
				):
					return row["line"]

		return None

	def store_sentence(self, owner, repo, pr_no, line):
		write_header = not self.path.exists()
		with open(self.path, "a") as f:
			writer = DictWriter(f, ["owner", "repo", "pr_no", "line"])

			if write_header:
				writer.writeheader()

			writer.writerow(
				{"owner": owner, "repo": repo, "pr_no": pr_no, "line": line}
			)


class SQLiteDatabase(Database):
	def __init__(self, path: Path):
		self.path = path
		self.conn = sqlite3.connect(path)
		self.cursor = self.conn.cursor()

	def get_sentence(self, owner, repo, pr_no):
		self._create_table()
		self.cursor.execute(
			"SELECT line FROM lines WHERE owner = ? AND repo = ? AND pr_no = ?",
			(owner, repo, pr_no),
		)
		result = self.cursor.fetchone()
		return result[0] if result else None

	def store_sentence(self, owner, repo, pr_no, line):
		self._create_table()

		self.cursor.execute(
			"INSERT INTO lines (owner, repo, pr_no, line) VALUES (?, ?, ?, ?)",
			(owner, repo, pr_no, line),
		)
		self.conn.commit()

	def _create_table(self):
		self.cursor.execute(
			"CREATE TABLE IF NOT EXISTS lines (owner TEXT, repo TEXT, pr_no TEXT, line TEXT)"
		)
		self.cursor.execute(
			"CREATE INDEX IF NOT EXISTS idx_owner_repo_pr_no ON lines (owner, repo, pr_no)"
		)
		self.conn.commit()
