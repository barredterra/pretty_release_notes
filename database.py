from csv import DictReader, DictWriter
from pathlib import Path
import sqlite3


class Database:
	def __init__(self, path: Path):
		self.path = path

	def get_sentence(self, owner, repo, pr_no) -> str | None:
		pass

	def store_sentence(self, owner, repo, pr_no, sentence) -> None:
		pass

	def delete_sentence(self, owner, repo, pr_no) -> None:
		pass


class CSVDatabase(Database):
	columns = ["owner", "repo", "pr_no", "sentence"]

	def get_sentence(self, owner, repo, pr_no):
		if not self.path.exists():
			return None

		with open(self.path, "r") as f:
			reader = DictReader(f, fieldnames=self.columns)
			for row in reader:
				if (
					row["owner"] == owner
					and row["repo"] == repo
					and row["pr_no"] == pr_no
				):
					return row["sentence"]

		return None

	def store_sentence(self, owner, repo, pr_no, sentence):
		write_header = not self.path.exists()
		with open(self.path, "a") as f:
			writer = DictWriter(f, self.columns)

			if write_header:
				writer.writeheader()

			writer.writerow(
				{"owner": owner, "repo": repo, "pr_no": pr_no, "sentence": sentence}
			)

	def delete_sentence(self, owner, repo, pr_no):
		with open(self.path, "r") as f:
			reader = DictReader(f, fieldnames=self.columns)
			rows = [
				row
				for row in reader
				if row["owner"] != owner or row["repo"] != repo or row["pr_no"] != pr_no
			]

		with open(self.path, "w") as f:
			writer = DictWriter(f, self.columns)
			writer.writeheader()
			writer.writerows(rows)


class SQLiteDatabase(Database):
	def __init__(self, path: Path):
		self.path = path
		self.conn = sqlite3.connect(path)
		self.cursor = self.conn.cursor()

	def get_sentence(self, owner, repo, pr_no):
		self._create_table()
		self.cursor.execute(
			"SELECT sentence FROM sentences WHERE owner = ? AND repo = ? AND pr_no = ?",
			(owner, repo, pr_no),
		)
		result = self.cursor.fetchone()
		return result[0] if result else None

	def store_sentence(self, owner, repo, pr_no, sentence):
		self._create_table()

		self.cursor.execute(
			"INSERT INTO sentences (owner, repo, pr_no, sentence) VALUES (?, ?, ?, ?)",
			(owner, repo, pr_no, sentence),
		)
		self.conn.commit()

	def delete_sentence(self, owner, repo, pr_no):
		self._create_table()
		self.cursor.execute(
			"DELETE FROM sentences WHERE owner = ? AND repo = ? AND pr_no = ?",
			(owner, repo, pr_no),
		)
		self.conn.commit()

	def _create_table(self):
		self.cursor.execute(
			"CREATE TABLE IF NOT EXISTS sentences (owner TEXT, repo TEXT, pr_no TEXT, sentence TEXT)"
		)
		self.cursor.execute(
			"CREATE INDEX IF NOT EXISTS idx_owner_repo_pr_no ON sentences (owner, repo, pr_no)"
		)
		self.conn.commit()
