"""Tests for database cache read semantics."""

import pytest

from pretty_release_notes.database import CSVDatabase, SQLiteDatabase
from pretty_release_notes.models import Repository


@pytest.fixture
def test_repo():
	return Repository(
		owner="test-owner",
		name="test-repo",
		url="https://api.github.com/repos/test-owner/test-repo",
		html_url="https://github.com/test-owner/test-repo",
	)


class TestGetSentenceReturnsLatest:
	def test_sqlite_returns_latest_row(self, tmp_path, test_repo):
		db = SQLiteDatabase(tmp_path / "test.sqlite")
		db.store_sentence(test_repo, "42", "First summary")
		db.store_sentence(test_repo, "42", "Second summary")

		assert db.get_sentence(test_repo, "42") == "Second summary"

	def test_csv_returns_latest_row(self, tmp_path, test_repo):
		db = CSVDatabase(tmp_path / "test.csv")
		db.store_sentence(test_repo, "42", "First summary")
		db.store_sentence(test_repo, "42", "Second summary")

		assert db.get_sentence(test_repo, "42") == "Second summary"

	def test_sqlite_missing_key_returns_none(self, tmp_path, test_repo):
		db = SQLiteDatabase(tmp_path / "test.sqlite")

		assert db.get_sentence(test_repo, "99") is None
