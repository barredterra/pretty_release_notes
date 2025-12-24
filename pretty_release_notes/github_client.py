import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .models import Issue, PullRequest, Repository
from .models.commit import Commit


class GitHubClient:
	"""Client to interact with the GitHub API."""

	def __init__(self, token: str):
		self.session = requests.Session()
		self.session.headers.update(
			{
				"Authorization": f"Bearer {token}",
			}
		)
		retries = Retry(
			total=3,
			backoff_factor=0.1,
			status_forcelist=[500, 502, 503, 504],
			allowed_methods=None,
		)
		self.session.mount("https://", HTTPAdapter(max_retries=retries))

	def get_repository(self, owner: str, name: str) -> Repository:
		"""Return a repository object."""
		r = self.session.get(
			f"https://api.github.com/repos/{owner}/{name}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		return Repository.from_dict(r.json())

	def get_closed_issues(self, repository: Repository, pr_no: str, first: int = 1) -> list[Issue]:
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
			for issue in response["data"]["repository"]["pullRequest"]["closingIssuesReferences"]["edges"]
		]

	def get_diff_commits(self, repository: Repository, tag: str, prev_tag: str) -> list[Commit]:
		"""Return a list of commits between two tags.

		Use this to get the commits for a tag that has a previous tag. Else, use get_tag_commits.
		"""
		r = self.session.get(
			f"{repository.url}/compare/{prev_tag}...{tag}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		data = r.json()

		return [Commit.from_dict(self, repository, commit) for commit in data.get("commits", [])]

	def get_tag_commits(self, repository: Repository, tag: str) -> list[Commit]:
		"""Return a list of commits for a given tag.

		Use this to get the commits for a tag that doesn't have a previous tag. Else, use get_diff_commits.
		"""
		params: dict[str, str | int] = {
			"sha": tag,
			"per_page": 100,
		}
		r = self.session.get(
			f"{repository.url}/commits",
			params=params,
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()

		commits = r.json()
		commits.sort(key=lambda x: x["commit"]["committer"]["date"])
		return [Commit.from_dict(self, repository, commit) for commit in commits]

	def get_commit_diff(self, repository: Repository, commit_sha: str) -> str:
		"""Return the diff of a particular commit."""
		r = self.session.get(
			f"{repository.url}/commits/{commit_sha}",
			headers={
				"Accept": "application/vnd.github.diff",
			},
		)
		r.raise_for_status()
		return r.text

	def get_pr(self, repository: Repository, pr_no: str) -> PullRequest:
		"""Get PR information from GitHub API."""
		r = self.session.get(
			f"{repository.url}/pulls/{pr_no}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		return PullRequest.from_dict(self, repository, r.json())

	def get_pr_patch(self, repository: Repository, pr_no: str) -> str:
		"""Return the patch of a PR."""
		r = self.session.get(
			f"{repository.url}/pulls/{pr_no}",
			headers={
				"Accept": "application/vnd.github.patch",
			},
		)

		try:
			r.raise_for_status()
		except requests.HTTPError:
			if r.status_code == 406:
				# patch is too big, return empty string
				return ""
			raise

		return r.text

	def get_pr_reviewers(self, repository: Repository, pr_no: str) -> set[str]:
		"""Get reviewers from GitHub API."""
		r = self.session.get(
			f"{repository.url}/pulls/{pr_no}/reviews",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		return {review["user"]["login"] for review in r.json()}

	def get_release(self, repository: Repository, tag: str):
		"""Get release information from GitHub API."""
		return self.session.get(
			f"{repository.url}/releases/tags/{tag}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		).json()

	def generate_release_notes(self, repository: Repository, tag: str, previous_tag_name: str | None = None):
		"""Generate release notes for a given tag.

		Args:
			repository: Repository object
			tag: Tag name for the release
			previous_tag_name: Optional previous tag to use as starting point for comparison
		"""
		json_payload = {"tag_name": tag}
		if previous_tag_name:
			json_payload["previous_tag_name"] = previous_tag_name

		response = self.session.post(
			f"{repository.url}/releases/generate-notes",
			headers={
				"Accept": "application/vnd.github+json",
			},
			json=json_payload,
		)

		response.raise_for_status()
		return response.json()

	def update_release(self, repository: Repository, release_id: str, body: str):
		"""Update release notes for a given tag."""
		response = self.session.patch(
			f"{repository.url}/releases/{release_id}",
			headers={
				"Accept": "application/vnd.github+json",
			},
			json={"body": body},
		)
		response.raise_for_status()
		return response.json()

	def get_commit_messages(self, url: str) -> list[str]:
		"""Get commit messages from GitHub API."""
		r = self.session.get(
			url,
			headers={
				"Accept": "application/json",
			},
		)
		r.raise_for_status()
		return [data["commit"]["message"] for data in r.json()]
