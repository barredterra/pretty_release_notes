import pytest

from github_client import GitHubClient
from models.pull_request import PullRequest
from models.repository import Repository


@pytest.fixture
def pull_request():
	return PullRequest(
		github=GitHubClient("test_token"),
		repository=Repository(
			owner="test_owner",
			name="test_name",
		),
		id=1,
		title="test_title",
		body="test_body",
		patch_url="test_patch_url",
	)


def test_backport_no(pull_request):
	pull_request.title = (
		"feat(regional): Address Template for Germany & Switzerland (backport #46737)"
	)
	assert pull_request.backport_no == "46737"

	pull_request.title = 'Revert "perf: timeout while renaming cost center (backport #46641)" (backport #46749)'
	assert pull_request.backport_no == "46749"


def test_from_dict():
	pull_request = PullRequest.from_dict(
		github=GitHubClient("test_token"),
		repository=Repository(
			owner="test_owner",
			name="test_name",
		),
		data={
			"number": 1,
			"title": "test_title",
			"body": "test_body",
			"patch_url": "test_patch_url",
			"commits_url": "test_commits_url",
			"user": {"login": "test_user"},
			"merged_by": {"login": "test_merged_by"},
			"labels": [{"name": "test_label"}],
		},
	)
	assert pull_request.id == 1
	assert pull_request.title == "test_title"
	assert pull_request.body == "test_body"
	assert pull_request.patch_url == "test_patch_url"
	assert pull_request.commits_url == "test_commits_url"
	assert pull_request.author == "test_user"
	assert pull_request.merged_by == "test_merged_by"
	assert pull_request.labels == {"test_label"}


def test_url(pull_request):
	assert pull_request.url == "https://github.com/test_owner/test_name/pull/1"
