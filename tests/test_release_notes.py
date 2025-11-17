from pretty_release_notes.core.config import GroupingConfig
from pretty_release_notes.github_client import GitHubClient
from pretty_release_notes.models.pull_request import PullRequest
from pretty_release_notes.models.release_notes import ReleaseNotes, ReleaseNotesLine
from pretty_release_notes.models.repository import Repository


def test_revert_filtering_in_same_release():
	"""Test that reverted PRs and their reverts are filtered from the same release."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="frappe",
		name="frappe",
		url="https://api.github.com/repos/frappe/frappe",
		html_url="https://github.com/frappe/frappe",
	)

	# Create a PR that will be reverted
	original_pr = PullRequest(
		github=github,
		repository=repo,
		id=100,
		title="feat: add new feature",
		body="Implements feature X",
		html_url="https://example.com/100",
	)

	# Create the revert PR
	revert_pr = PullRequest(
		github=github,
		repository=repo,
		id=105,
		title='Revert "feat: add new feature"',
		body="Reverts frappe/frappe#100\n\nThis broke production",
		html_url="https://example.com/105",
	)

	# Create another unrelated PR
	other_pr = PullRequest(
		github=github,
		repository=repo,
		id=102,
		title="fix: unrelated bug fix",
		body="Fixes issue Y",
		html_url="https://example.com/102",
	)

	# Build release notes with all three PRs
	lines = [
		ReleaseNotesLine(original_line="", change=original_pr, sentence="Added new feature X"),
		ReleaseNotesLine(original_line="", change=other_pr, sentence="Fixed issue Y"),
		ReleaseNotesLine(original_line="", change=revert_pr, sentence="Reverted feature X"),
	]

	release_notes = ReleaseNotes(lines=lines)

	# Serialize without any filters
	output = release_notes.serialize()

	# Both the original and revert should be excluded
	assert "Added new feature X" not in output
	assert "Reverted feature X" not in output
	# The unrelated PR should still be included
	assert "Fixed issue Y" in output


def test_revert_without_original_in_release():
	"""Test that a revert PR appears if the original is not in the same release."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="frappe",
		name="frappe",
		url="https://api.github.com/repos/frappe/frappe",
		html_url="https://github.com/frappe/frappe",
	)

	# Create a revert PR for a PR not in this release
	revert_pr = PullRequest(
		github=github,
		repository=repo,
		id=200,
		title='Revert "feat: old feature"',
		body="Reverts frappe/frappe#50\n\nReverting old feature",
		html_url="https://example.com/200",
	)

	lines = [
		ReleaseNotesLine(original_line="", change=revert_pr, sentence="Reverted old feature"),
	]

	release_notes = ReleaseNotes(lines=lines)
	output = release_notes.serialize()

	# The revert should appear since the original PR #50 is not in this release
	assert "Reverted old feature" in output


def test_revert_filtering_with_excluded_original():
	"""Test that revert PRs are filtered even if the original PR is excluded by type."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="frappe",
		name="frappe",
		url="https://api.github.com/repos/frappe/frappe",
		html_url="https://github.com/frappe/frappe",
	)

	# Create a PR that will be filtered out by type
	original_pr = PullRequest(
		github=github,
		repository=repo,
		id=100,
		title="chore: update dependencies",
		body="Updates dependencies",
		html_url="https://example.com/100",
	)

	# Create the revert PR
	revert_pr = PullRequest(
		github=github,
		repository=repo,
		id=105,
		title='Revert "chore: update dependencies"',
		body="Reverts frappe/frappe#100\n\nThis broke something",
		html_url="https://example.com/105",
	)

	# Create another unrelated PR
	other_pr = PullRequest(
		github=github,
		repository=repo,
		id=102,
		title="fix: unrelated bug fix",
		body="Fixes issue Y",
		html_url="https://example.com/102",
	)

	# Build release notes with all three PRs
	lines = [
		ReleaseNotesLine(original_line="", change=original_pr, sentence="Updated dependencies"),
		ReleaseNotesLine(original_line="", change=other_pr, sentence="Fixed issue Y"),
		ReleaseNotesLine(original_line="", change=revert_pr, sentence="Reverted dependency update"),
	]

	release_notes = ReleaseNotes(lines=lines)

	# Serialize with type filter (exclude "chore")
	output = release_notes.serialize(exclude_change_types={"chore"})

	# The original chore PR should be filtered by type
	assert "Updated dependencies" not in output
	# The revert should ALSO be excluded because it reverts a PR in this release
	assert "Reverted dependency update" not in output
	# The unrelated PR should still be included
	assert "Fixed issue Y" in output


def test_group_by_type_with_multiple_types():
	"""Test grouping release notes by conventional commit type."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="test_org",
		name="test_repo",
		url="https://api.github.com/repos/test_org/test_repo",
		html_url="https://github.com/test_org/test_repo",
	)

	# Create PRs with different types
	feat_pr1 = PullRequest(
		github=github,
		repository=repo,
		id=1,
		title="feat: add new dashboard",
		body="",
		html_url="https://github.com/org/repo/pull/1",
	)

	feat_pr2 = PullRequest(
		github=github,
		repository=repo,
		id=2,
		title="feat(ui): improve navigation",
		body="",
		html_url="https://github.com/org/repo/pull/2",
	)

	fix_pr = PullRequest(
		github=github,
		repository=repo,
		id=3,
		title="fix: resolve login bug",
		body="",
		html_url="https://github.com/org/repo/pull/3",
	)

	no_type_pr = PullRequest(
		github=github,
		repository=repo,
		id=4,
		title="Update dependencies",
		body="",
		html_url="https://github.com/org/repo/pull/4",
	)

	# Create release notes
	lines = [
		ReleaseNotesLine(original_line="", change=feat_pr1, sentence="Added new dashboard"),
		ReleaseNotesLine(original_line="", change=feat_pr2, sentence="Improved navigation"),
		ReleaseNotesLine(original_line="", change=fix_pr, sentence="Fixed login bug"),
		ReleaseNotesLine(original_line="", change=no_type_pr, sentence="Updated dependencies"),
	]

	release_notes = ReleaseNotes(lines=lines)

	# Test with grouping enabled
	grouping = GroupingConfig(group_by_type=True)
	output = release_notes.serialize(grouping=grouping)

	# Verify sections are created
	assert "## Features" in output
	assert "## Bug Fixes" in output
	assert "## Other Changes" in output

	# Verify items are in correct sections
	lines_output = output.split("\n")
	feat_section_start = lines_output.index("## Features")
	fix_section_start = lines_output.index("## Bug Fixes")
	other_section_start = lines_output.index("## Other Changes")

	# Features should come before fixes
	assert feat_section_start < fix_section_start

	# Both feature PRs should be in Features section
	features_text = "\n".join(lines_output[feat_section_start:fix_section_start])
	assert "Added new dashboard" in features_text
	assert "Improved navigation" in features_text

	# Fix should be in Bug Fixes section
	fixes_text = "\n".join(lines_output[fix_section_start:other_section_start])
	assert "Fixed login bug" in fixes_text

	# No-type PR should be in Other Changes
	other_text = "\n".join(lines_output[other_section_start:])
	assert "Updated dependencies" in other_text


def test_group_by_type_with_filtering():
	"""Test that filtering works with grouping."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="test_org",
		name="test_repo",
		url="https://api.github.com/repos/test_org/test_repo",
		html_url="https://github.com/test_org/test_repo",
	)

	feat_pr = PullRequest(
		github=github,
		repository=repo,
		id=1,
		title="feat: add feature",
		body="",
		html_url="https://github.com/org/repo/pull/1",
	)

	chore_pr = PullRequest(
		github=github,
		repository=repo,
		id=2,
		title="chore: update deps",
		body="",
		html_url="https://github.com/org/repo/pull/2",
	)

	lines = [
		ReleaseNotesLine(original_line="", change=feat_pr, sentence="Added feature"),
		ReleaseNotesLine(original_line="", change=chore_pr, sentence="Updated deps"),
	]

	release_notes = ReleaseNotes(lines=lines)

	# Test with grouping and filtering
	grouping = GroupingConfig(group_by_type=True)
	output = release_notes.serialize(exclude_change_types={"chore"}, grouping=grouping)

	# Feature should be included
	assert "## Features" in output
	assert "Added feature" in output

	# Chore should be filtered out
	assert "Updated deps" not in output
	# No "Chores" section should exist
	assert "## Chores" not in output


def test_group_by_type_disabled():
	"""Test that grouping can be disabled (default behavior)."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="test_org",
		name="test_repo",
		url="https://api.github.com/repos/test_org/test_repo",
		html_url="https://github.com/test_org/test_repo",
	)

	pr1 = PullRequest(
		github=github,
		repository=repo,
		id=1,
		title="feat: add feature",
		body="",
		html_url="https://github.com/org/repo/pull/1",
	)

	pr2 = PullRequest(
		github=github,
		repository=repo,
		id=2,
		title="fix: fix bug",
		body="",
		html_url="https://github.com/org/repo/pull/2",
	)

	lines = [
		ReleaseNotesLine(original_line="", change=pr1, sentence="Added feature"),
		ReleaseNotesLine(original_line="", change=pr2, sentence="Fixed bug"),
	]

	release_notes = ReleaseNotes(lines=lines)

	# Test with grouping disabled (or not provided)
	output = release_notes.serialize()

	# Should not have section headers
	assert "## Features" not in output
	assert "## Bug Fixes" not in output

	# Should be flat list
	assert "* Added feature" in output
	assert "* Fixed bug" in output
