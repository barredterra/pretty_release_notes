from typing import cast

from requests.adapters import HTTPAdapter

from pretty_release_notes.github_client import GitHubClient


def test_reads_retry_but_comment_and_label_writes_do_not():
	# After a 502 or 504, GitHub may already have applied a write. A retry could add a duplicate comment.
	client = GitHubClient("gh-token")

	read_adapter = cast(HTTPAdapter, client.session.get_adapter("https://api.github.com"))
	write_adapter = cast(HTTPAdapter, client.write_session.get_adapter("https://api.github.com"))

	assert read_adapter.max_retries.total == 3
	assert write_adapter.max_retries.total == 0
	assert client.write_session.headers["Authorization"] == "Bearer gh-token"
