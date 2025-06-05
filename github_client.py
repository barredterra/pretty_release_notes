import requests

from models import Issue, PullRequest, Repository
from models.commit import Commit


class GitHubClient:
	"""Client to interact with the GitHub API."""

	def __init__(self, token: str):
		self.session = requests.Session()
		self.session.headers.update(
			{
				"Authorization": f"Bearer {token}",
			}
		)

	def get_text(self, url: str) -> str:
		"""Get patch from GitHub API."""
		return self.session.get(url).text

	def get_closed_issues(
		self, repository: Repository, pr_no: str, first: int = 1
	) -> list[Issue]:
		"""Get a list of issues (title and body) that are closed by a PR."""
		response = self.session.post(
			"https://api.github.com/graphql",
			json={
				"query": """
					query($owner: String!, $name: String!, $pr_no: Int!, $first: Int!) {
						repository(owner: $owner, name: $name) {
							pullRequest(number: $pr_no) {
								closingIssuesReferences (first: $first) {
									edges {
										node {
											body
											title
										}
									}
								}
							}
						}
					}
				""",
				"variables": {
					"owner": repository.owner,
					"name": repository.name,
					"pr_no": int(pr_no),
					"first": first,
				},
			},
		).json()

		if "data" not in response:
			return []

		return [
			Issue.from_dict(issue["node"])
			for issue in response["data"]["repository"]["pullRequest"][
				"closingIssuesReferences"
			]["edges"]
		]

	def get_diff_commits(
		self, repository: Repository, tag: str, prev_tag: str
	) -> list[Commit]:
		"""Return a list of commits between two tags."""
		r = self.session.get(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/compare/{prev_tag}...{tag}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		data = r.json()

		return [
			Commit.from_dict(self, repository, commit)
			for commit in data.get("commits", [])
		]

	def get_pr(self, repository: Repository, pr_no: str) -> PullRequest:
		"""Get PR information from GitHub API."""
		r = self.session.get(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/pulls/{pr_no}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		return PullRequest.from_dict(self, repository, r.json())

	def get_pr_reviewers(self, repository: Repository, pr_no: str) -> set[str]:
		"""Get reviewers from GitHub API."""
		r = self.session.get(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/pulls/{pr_no}/reviews",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		return {review["user"]["login"] for review in r.json()}

	def get_release(self, repository: Repository, tag: str):
		"""Get release information from GitHub API."""
		return self.session.get(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/releases/tags/{tag}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		).json()

	def generate_release_notes(self, repository: Repository, tag: str):
		"""Generate release notes for a given tag."""
		response = self.session.post(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/releases/generate-notes",
			headers={
				"Accept": "application/vnd.github+json",
			},
			json={"tag_name": tag},
		)

		response.raise_for_status()
		return response.json()

	def update_release(self, repository: Repository, release_id: str, body: str):
		"""Update release notes for a given tag."""
		response = self.session.patch(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/releases/{release_id}",
			headers={
				"Accept": "application/vnd.github+json",
			},
			json={"body": body},
		)
		response.raise_for_status()
		return response.json()

	def get_commit_messages(self, url):
		"""Get commit messages from GitHub API."""
		return self.session.get(
			url,
			headers={
				"Accept": "application/json",
			},
		).json()
