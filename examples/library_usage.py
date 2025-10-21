"""Example of using pretty_release_notes as a library."""

from pathlib import Path

from pretty_release_notes import ProgressEvent, ProgressReporter, ReleaseNotesBuilder


class CustomProgressReporter(ProgressReporter):
	"""Custom progress reporter that logs to console."""

	def report(self, event: ProgressEvent) -> None:
		print(f"[{event.type.upper()}] {event.message[:100]}")


# Example 1: Basic usage with minimal configuration
def basic_usage():
	"""Generate release notes with minimal configuration."""
	client = (
		ReleaseNotesBuilder()
		.with_github_token("ghp_xxxxx")  # Replace with your token
		.with_openai("sk-xxxxx")  # Replace with your API key
		.build()
	)

	notes = client.generate_release_notes(
		owner="frappe",
		repo="erpnext",
		tag="v15.38.4",
	)

	print(notes)


# Example 2: Advanced usage with custom configuration
def advanced_usage():
	"""Generate release notes with custom filters and progress reporting."""
	client = (
		ReleaseNotesBuilder()
		.with_github_token("ghp_xxxxx")  # Replace with your token
		.with_openai("sk-xxxxx", model="gpt-4", max_patch_size=15000)
		.with_database("sqlite", enabled=True)
		.with_filters(
			exclude_types={"chore", "refactor", "ci", "style", "test"},
			exclude_labels={"skip-release-notes"},
			exclude_authors={"dependabot[bot]", "github-actions[bot]"},
		)
		.with_prompt_file(Path("custom_prompt.txt"))
		.with_force_commits(False)
		.with_progress_reporter(CustomProgressReporter())
		.build()
	)

	notes = client.generate_release_notes(
		owner="frappe",
		repo="erpnext",
		tag="v15.38.4",
	)

	print(notes)

	# Optionally update GitHub release
	# client.update_github_release("frappe", "erpnext", "v15.38.4", notes)


# Example 3: Direct configuration (without builder)
def direct_config_usage():
	"""Generate release notes using direct configuration."""
	from pretty_release_notes import (
		DatabaseConfig,
		FilterConfig,
		GitHubConfig,
		OpenAIConfig,
		ReleaseNotesClient,
		ReleaseNotesConfig,
	)

	config = ReleaseNotesConfig(
		github=GitHubConfig(token="ghp_xxxxx"),  # Replace with your token
		openai=OpenAIConfig(api_key="sk-xxxxx", model="gpt-4.1"),  # Replace with your key
		database=DatabaseConfig(type="sqlite", enabled=True),
		filters=FilterConfig(
			exclude_change_types={"chore", "refactor"},
			exclude_change_labels={"skip-release-notes"},
		),
	)

	client = ReleaseNotesClient(config, progress_reporter=CustomProgressReporter())

	notes = client.generate_release_notes(
		owner="frappe",
		repo="erpnext",
		tag="v15.38.4",
	)

	print(notes)


# Example 4: Silent operation (no progress reporting)
def silent_usage():
	"""Generate release notes without any progress output."""
	client = (
		ReleaseNotesBuilder()
		.with_github_token("ghp_xxxxx")  # Replace with your token
		.with_openai("sk-xxxxx")  # Replace with your API key
		.build()
	)  # No progress reporter = NullProgressReporter used by default

	notes = client.generate_release_notes(
		owner="frappe",
		repo="erpnext",
		tag="v15.38.4",
	)

	return notes


if __name__ == "__main__":
	print("Example 1: Basic Usage")
	print("=" * 80)
	# Uncomment to run:
	# basic_usage()

	print("\nExample 2: Advanced Usage with Custom Configuration")
	print("=" * 80)
	# Uncomment to run:
	# advanced_usage()

	print("\nExample 3: Direct Configuration")
	print("=" * 80)
	# Uncomment to run:
	# direct_config_usage()

	print("\nExample 4: Silent Operation")
	print("=" * 80)
	# Uncomment to run:
	# result = silent_usage()
	# print(result)

	print("\nReplace 'ghp_xxxxx' and 'sk-xxxxx' with valid tokens to run these examples.")
