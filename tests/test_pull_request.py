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
