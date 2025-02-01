import re
from dataclasses import dataclass

import requests


@dataclass
class Repository:
	owner: str
	name: str

	@property
	def url(self):
		return f"https://github.com/{self.owner}/{self.name}"


@dataclass
class Issue:
	title: str
	body: str

	@classmethod
	def from_dict(cls, data: dict) -> "Issue":
		return cls(
			title=data["title"],
			body=data["body"],
		)

	def __str__(self):
		return f"""Issue Title: {self.title}\n\nIssue Body: {self.body}"""


@dataclass
class PullRequest:
	repository: Repository
	number: int
	title: str
	body: str
	patch_url: str
	commits_url: str | None = None

	@property
	def url(self):
		return f"{self.repository.url}/pull/{self.number}"

	@property
	def backport_no(self) -> str | None:
		original_pr_match = re.search(r"\(backport #(\d+)\)", self.title)
		return original_pr_match[1] if original_pr_match else None

	@classmethod
	def from_dict(cls, repository: Repository, data: dict) -> "PullRequest":
		return cls(
			repository=repository,
			number=data["number"],
			title=data["title"],
			body=data["body"],
			patch_url=data["patch_url"],
			commits_url=data["commits_url"],
		)

	def __str__(self):
		return f"""PR Title: {self.title}\n\nPR Body: {self.body}"""


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
	) -> list["Issue"]:
		"""Get a list of issues (title and body) that are closed by a PR."""
		response = self.session.post(
			"https://api.github.com/graphql",
			json={
				"query": f"""
					query {{
						repository(owner: "{repository.owner}", name: "{repository.name}") {{
							pullRequest(number: {pr_no}) {{
								closingIssuesReferences (first: {first}) {{
									edges {{
										node {{
											body
											title
										}}
									}}
								}}
							}}
						}}
					}}
				"""
			},
		).json()

		if "data" not in response:
			return []

		return [
			Issue.from_dict(issue)
			for issue in response["data"]["repository"]["pullRequest"][
				"closingIssuesReferences"
			]["edges"]
		]

	def get_pr(self, repository: Repository, pr_no: str) -> "PullRequest":
		"""Get PR information from GitHub API."""
		r = self.session.get(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/pulls/{pr_no}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		)
		r.raise_for_status()
		return PullRequest.from_dict(repository, r.json())

	def get_release(self, repository: Repository, tag: str):
		"""Get release information from GitHub API."""
		return self.session.get(
			f"https://api.github.com/repos/{repository.owner}/{repository.name}/releases/tags/{tag}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		).json()

	def get_commit_messages(self, url):
		"""Get commit messages from GitHub API."""
		return self.session.get(
			url,
			headers={
				"Accept": "application/json",
			},
		).json()
