"""Tests for models utility functions."""

from pretty_release_notes.models._utils import get_conventional_type


class TestGetConventionalType:
	"""Test conventional commit type extraction."""

	def test_basic_types(self):
		"""Test extraction of basic conventional commit types."""
		assert get_conventional_type("feat: add new feature") == "feat"
		assert get_conventional_type("fix: resolve bug") == "fix"
		assert get_conventional_type("docs: update readme") == "docs"
		assert get_conventional_type("perf: improve performance") == "perf"
		assert get_conventional_type("refactor: restructure code") == "refactor"
		assert get_conventional_type("test: add tests") == "test"
		assert get_conventional_type("build: update build") == "build"
		assert get_conventional_type("ci: update CI") == "ci"
		assert get_conventional_type("chore: update deps") == "chore"
		assert get_conventional_type("style: format code") == "style"
		assert get_conventional_type("revert: revert changes") == "revert"

	def test_with_scope(self):
		"""Test extraction with scope in parentheses."""
		assert get_conventional_type("feat(ui): add button") == "feat"
		assert get_conventional_type("fix(api): resolve endpoint issue") == "fix"
		assert get_conventional_type("docs(readme): update examples") == "docs"

	def test_case_insensitive(self):
		"""Test that type extraction is case-insensitive."""
		assert get_conventional_type("Fix: resolve bug") == "fix"
		assert get_conventional_type("FIX: resolve bug") == "fix"
		assert get_conventional_type("Feat: add feature") == "feat"
		assert get_conventional_type("FEAT: add feature") == "feat"

	def test_with_leading_whitespace(self):
		"""Test that leading whitespace is handled correctly."""
		assert get_conventional_type(" fix: resolve bug") == "fix"
		assert get_conventional_type("  feat: add feature") == "feat"
		assert get_conventional_type("\tfix: resolve bug") == "fix"
		assert get_conventional_type(" Fix: resolve bug") == "fix"

	def test_with_trailing_whitespace(self):
		"""Test that trailing whitespace doesn't affect extraction."""
		assert get_conventional_type("fix: resolve bug ") == "fix"
		assert get_conventional_type("feat: add feature  ") == "feat"

	def test_non_conventional_format(self):
		"""Test that non-conventional formats return None."""
		assert get_conventional_type("Add new feature") is None
		assert get_conventional_type("Update dependencies") is None
		assert get_conventional_type("Bug fix") is None
		assert get_conventional_type("Fix : with space before colon") is None

	def test_edge_cases(self):
		"""Test edge cases."""
		assert get_conventional_type("") is None
		assert get_conventional_type("  ") is None
		assert get_conventional_type("a:") is None  # Too short (< 2 chars)
		assert get_conventional_type("x: message") is None  # Too short (< 2 chars)
		assert get_conventional_type("ab: message") == "ab"  # Exactly 2 chars
		assert get_conventional_type("refactor: message") == "refactor"  # 8 chars (max)
		assert get_conventional_type("verylongtype: message") is None  # 12 chars (> 8)

	def test_real_world_examples(self):
		"""Test real-world PR title examples."""
		assert get_conventional_type("feat(regional): Address Template for Germany & Switzerland") == "feat"
		assert get_conventional_type('Revert "perf: timeout while renaming cost center"') is None
		assert get_conventional_type(" Fix: Product Bundle Purchase Order Creation Logic") == "fix"
		assert get_conventional_type("fix(accounting): correct tax calculation") == "fix"
