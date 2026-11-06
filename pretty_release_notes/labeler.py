"""Add a release label and a release comment to the PRs of a release."""

import re
import time

from .generator import get_previous_tag_name
from .github_client import GitHubClient
from .models import Repository

# Seconds to wait after each write. GitHub limits content creation to 80 writes per minute.
WRITE_DELAY = 1.0


def label_release(github: GitHubClient, repository: Repository, tag: str, label: str) -> None:
	"""Comment on and label each PR of a release that does not have the label yet.

	Raise on the first failed request. Labeled PRs are skipped, so a retry continues with the rest.
	"""
	release = github.get_release(repository, tag)
	previous_tag = get_previous_tag_name(release["body"] or "", repository)
	notes = github.generate_release_notes(repository, tag, previous_tag)
	pr_numbers = get_pr_numbers(notes["body"], repository)
	if not pr_numbers:
		return

	labels_by_pr = github.get_pr_labels(repository, pr_numbers)
	unlabeled = [pr_no for pr_no in pr_numbers if label not in labels_by_pr[pr_no]]

	release_url = f"{repository.html_url}/releases/tag/{tag}"
	version = tag.removeprefix("v")
	comment = (
		f":tada: This PR is included in version {version} :tada:\n\n"
		f"The release is available on [GitHub release]({release_url})"
	)

	for pr_no in unlabeled:
		# Comment first: if we stop between the two writes, the next run adds a
		# second comment instead of leaving the PR without one.
		github.add_comment(repository, pr_no, comment)
		time.sleep(WRITE_DELAY)
		github.add_labels(repository, pr_no, [label])
		time.sleep(WRITE_DELAY)


def get_pr_numbers(release_notes: str, repository: Repository) -> list[int]:
	"""Return the unique PR numbers of this repository in the release notes, in order."""
	pr_url = re.escape(f"https://github.com/{repository.owner}/{repository.name}/pull/") + r"(\d+)"
	matches = re.findall(pr_url, release_notes, flags=re.IGNORECASE)
	return list(dict.fromkeys(int(pr_no) for pr_no in matches))
