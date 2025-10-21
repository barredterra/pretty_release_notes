import pytest

from pretty_release_notes.github_client import GitHubClient
from pretty_release_notes.models.pull_request import PullRequest
from pretty_release_notes.models.repository import Repository


@pytest.fixture
def pull_request():
	return PullRequest(
		github=GitHubClient("test_token"),
		repository=Repository(
			owner="test_owner",
			name="test_name",
			url="test_url",
			html_url="test_html_url",
		),
		id=1,
		title="test_title",
		body="test_body",
		html_url="test_html_url",
	)


def test_backport_no(pull_request):
	pull_request.title = "feat(regional): Address Template for Germany & Switzerland (backport #46737)"
	assert pull_request.backport_no == "46737"

	pull_request.title = 'Revert "perf: timeout while renaming cost center (backport #46641)" (backport #46749)'
	assert pull_request.backport_no == "46749"


def test_conventional_type(pull_request):
	pull_request.title = "feat(regional): Address Template for Germany & Switzerland"
	assert pull_request.conventional_type == "feat"

	pull_request.title = 'Revert "perf: timeout while renaming cost center"'
	assert pull_request.conventional_type is None


def test_from_dict():
	pull_request = PullRequest.from_dict(
		github=GitHubClient("test_token"),
		repository=Repository(
			owner="test_owner",
			name="test_name",
			url="test_url",
			html_url="test_html_url",
		),
		data={
			"number": 1,
			"title": "test_title",
			"body": "test_body",
			"html_url": "test_html_url",
			"commits_url": "test_commits_url",
			"user": {"login": "test_user"},
			"merged_by": {"login": "test_merged_by"},
			"labels": [{"name": "test_label"}],
		},
	)
	assert pull_request.id == 1
	assert pull_request.title == "test_title"
	assert pull_request.body == "test_body"
	assert pull_request.html_url == "test_html_url"
	assert pull_request.commits_url == "test_commits_url"
	assert pull_request.author == "test_user"
	assert pull_request.merged_by == "test_merged_by"
	assert pull_request.labels == {"test_label"}
