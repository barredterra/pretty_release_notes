import typer
from rich.console import Console
from rich.markdown import Markdown


class CLI:
	def __init__(self):
		self.console = Console()

	def show_markdown_text(self, text: str) -> None:
		self.console.print(Markdown(text))

	def show_release_notes(self, heading: str, release_notes: str) -> None:
		"""Show release notes in a markdown format.

		Args:
			heading (str): The heading of the release notes (without leading #).
			release_notes (str): The release notes to show (in markdown format).
		"""
		self.show_markdown_text(f"# {heading}")
		self.show_markdown_text(release_notes)

	def confirm_update(self) -> bool:
		"""Confirm if the user wants to update the release notes.

		Returns:
			bool: True if the user wants to update the release notes, False otherwise.
		"""
		return typer.confirm("Update release notes?")

	def show_error(self, message: str) -> None:
		"""Show a red error message, to stderr.

		Args:
			message (str): The error message to show.
		"""
		typer.echo(message, err=True, color=typer.colors.RED)

	def show_success(self, message: str) -> None:
		"""Show a green success message, to stdout.

		Args:
			message (str): The success message to show.
		"""
		typer.echo(message, color=typer.colors.GREEN)
