import sqlite3
from csv import DictReader, DictWriter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from models import Repository


class Database:
	def __init__(self, path: Path):
		self.path = path

	def get_sentence(self, repository: "Repository", pr_no: str) -> str | None:
		pass

	def store_sentence(
		self, repository: "Repository", pr_no: str, sentence: str
	) -> None:
		pass

	def delete_sentence(self, repository: "Repository", pr_no: str) -> None:
		pass


class CSVDatabase(Database):
	columns = ["owner", "repo", "pr_no", "sentence"]

	def get_sentence(self, repository: "Repository", pr_no: str) -> str | None:
		if not self.path.exists():
			return None

		with open(self.path, "r") as f:
			reader = DictReader(f, fieldnames=self.columns)
			for row in reader:
				if (
					row["owner"] == repository.owner
					and row["repo"] == repository.name
					and row["pr_no"] == pr_no
				):
					return row["sentence"]

		return None

	def store_sentence(
		self, repository: "Repository", pr_no: str, sentence: str
	) -> None:
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
		with open(self.path, "r") as f:
			reader = DictReader(f, fieldnames=self.columns)
			rows = [
				row
				for row in reader
				if row["owner"] != repository.owner
				or row["repo"] != repository.name
				or row["pr_no"] != pr_no
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

	def get_sentence(self, repository: "Repository", pr_no: str) -> str | None:
		self._create_table()
		self.cursor.execute(
			"SELECT sentence FROM sentences WHERE owner = ? AND repo = ? AND pr_no = ?",
			(repository.owner, repository.name, pr_no),
		)
		result = self.cursor.fetchone()
		return result[0] if result else None

	def store_sentence(
		self, repository: "Repository", pr_no: str, sentence: str
	) -> None:
		self._create_table()

		self.cursor.execute(
			"INSERT INTO sentences (owner, repo, pr_no, sentence) VALUES (?, ?, ?, ?)",
			(repository.owner, repository.name, pr_no, sentence),
		)
		self.conn.commit()

	def delete_sentence(self, repository: "Repository", pr_no: str) -> None:
		self._create_table()
		self.cursor.execute(
			"DELETE FROM sentences WHERE owner = ? AND repo = ? AND pr_no = ?",
			(repository.owner, repository.name, pr_no),
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
