from pathlib import Path
import typer
from dotenv import dotenv_values

from generator import ReleaseNotesGenerator
from ui import CLI

app = typer.Typer()
config = dotenv_values(".env")


@app.command()
def main(repo: str, tag: str, owner: str | None = None, database: bool = True, prompt_path: Path | None = None):
	cli = CLI()
	generator = ReleaseNotesGenerator(
		owner=owner or config["DEFAULT_OWNER"],
		repo=repo,
		prompt_path=prompt_path or Path("prompt.txt"),
		github_token=config["GH_TOKEN"],
		openai_model=config["OPENAI_MODEL"],
		openai_api_key=config["OPENAI_API_KEY"],
		exclude_pr_types=get_config_set("EXCLUDE_PR_TYPES"),
		exclude_pr_labels=get_config_set("EXCLUDE_PR_LABELS"),
		exclude_authors=get_config_set("EXCLUDE_AUTHORS"),
		db_type=config["DB_TYPE"],
		ui=cli,
		max_patch_size=int(config["MAX_PATCH_SIZE"]),
		use_db=database,
	)
	notes = generator.generate(tag)
	cli.show_release_notes("New Release Notes", notes)

	if cli.confirm_update():
		generator.update_on_github(notes, tag)


def get_config_set(key: str) -> set[str]:
	return set(config[key].split(",")) if config[key] else set()


if __name__ == "__main__":
	app()
