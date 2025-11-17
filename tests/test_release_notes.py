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
