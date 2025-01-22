import requests


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
		self, owner: str, repo: str, pr_no: str, first: int = 1
	) -> list[dict]:
		"""Get a list of issues (title and body) that are closed by a PR."""
		response = self.session.post(
			"https://api.github.com/graphql",
			json={
				"query": f"""
					query {{
						repository(owner: "{owner}", name: "{repo}") {{
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

		return response["data"]["repository"]["pullRequest"]["closingIssuesReferences"][
			"edges"
		]

	def get_pr(self, owner: str, repo: str, pr_no: str) -> dict:
		"""Get PR information from GitHub API."""
		return self.session.get(
			f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_no}",
			headers={
				"Accept": "application/vnd.github+json",
			},
		).json()

	def get_release(self, owner: str, repo: str, tag: str):
		"""Get release information from GitHub API."""
		return self.session.get(
			f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}",
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
