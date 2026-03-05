from unittest.mock import patch

from pretty_release_notes.github_client import GitHubClient
from pretty_release_notes.models.pull_request import PullRequest
from pretty_release_notes.models.repository import Repository


def test_is_revert_detection():
	"""Test that revert PRs are correctly identified."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="frappe",
		name="frappe",
		url="https://api.github.com/repos/frappe/frappe",
		html_url="https://github.com/frappe/frappe",
	)

	# Test various revert patterns
	test_cases = [
		("Reverts frappe/frappe#12345", True, "12345"),
		("Reverts https://github.com/frappe/frappe/pull/12345", True, "12345"),
		("Reverts #12345", True, "12345"),
		("reverts frappe/frappe#12345", True, "12345"),  # Lowercase
		("reverts https://github.com/frappe/frappe/pull/12345", True, "12345"),  # Lowercase
		("reverts #12345", True, "12345"),  # Lowercase
		("This reverts commit abc123", False, None),  # Git revert, not PR revert
		("Regular PR body", False, None),
		("", False, None),
	]

	for body_text, expected_is_revert, expected_pr_num in test_cases:
		pr = PullRequest(
			github=github,
			repository=repo,
			id=100,
			title="Test PR",
			body=body_text,
			html_url="https://example.com",
		)

		assert pr.is_revert == expected_is_revert, f"Failed for body: {body_text}"
		assert pr.reverted_pr_number == expected_pr_num, f"Failed to extract PR number from: {body_text}"


def test_revert_with_backport():
	"""Test that a revert of a backport is handled correctly."""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="frappe",
		name="frappe",
		url="https://api.github.com/repos/frappe/frappe",
		html_url="https://github.com/frappe/frappe",
	)

	pr = PullRequest(
		github=github,
		repository=repo,
		id=200,
		title='Revert "fix: something (backport #150)" (backport #200)',
		body="Reverts frappe/frappe#150",
		html_url="https://example.com",
	)

	assert pr.is_revert is True
	assert pr.reverted_pr_number == "150"
	assert pr.backport_no == "200"  # Should still detect backport


def test_get_author_chained_backports():
	"""Test that get_author() traverses the full backport chain.

	Chain: PR4 (backport of PR3) -> PR3 (backport of PR2) -> PR2 (backport of PR1) -> PR1 (original)
	get_author() on PR4 should return PR1's author, not PR3's or PR2's author.
	"""
	github = GitHubClient("test_token")
	repo = Repository(
		owner="frappe",
		name="frappe",
		url="https://api.github.com/repos/frappe/frappe",
		html_url="https://github.com/frappe/frappe",
	)

	pr1 = PullRequest(
		github=github,
		repository=repo,
		id=1,
		title="feat: original feature",
		body="",
		html_url="https://example.com/1",
		author="original_author",
	)
	pr2 = PullRequest(
		github=github,
		repository=repo,
		id=2,
		title="feat: original feature (backport #1)",
		body="",
		html_url="https://example.com/2",
		author="mergify[bot]",
		backport_of=pr1,
	)
	pr3 = PullRequest(
		github=github,
		repository=repo,
		id=3,
		title="feat: original feature (backport #2)",
		body="",
		html_url="https://example.com/3",
		author="mergify[bot]",
		backport_of=pr2,
	)
	pr4 = PullRequest(
		github=github,
		repository=repo,
		id=4,
		title="feat: original feature (backport #3)",
		body="",
		html_url="https://example.com/4",
		author="mergify[bot]",
		backport_of=pr3,
	)

	# Mock _set_backport_of to avoid GitHub API calls; backport_of is pre-set above
	with patch.object(PullRequest, "_set_backport_of"):
		assert pr1.get_author() == "original_author"
		assert pr2.get_author() == "original_author"
		assert pr3.get_author() == "original_author"
		assert pr4.get_author() == "original_author"
