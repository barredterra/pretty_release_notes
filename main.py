import hashlib
import hmac
from pathlib import Path

import typer
from dotenv import dotenv_values
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse

from generator import ReleaseNotesGenerator
from ui import CLI

# Typer CLI app
cli_app = typer.Typer()

# FastAPI app for webhooks
api_app = FastAPI(title="Pretty Release Notes API", version="1.0.0")

config = dotenv_values(".env")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature[7:], expected_signature)


@api_app.post("/webhook/release")
async def handle_release_webhook(request: Request):
    """Handle GitHub release webhook"""
    
    # Get webhook secret from environment
    webhook_secret = config.get("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    # Get the signature from headers
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing signature header"
        )
    
    # Get the payload
    payload = await request.body()
    
    # Verify signature
    if not verify_webhook_signature(payload, signature, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Parse the JSON payload
    try:
        webhook_data = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Check if it's a release event
    if webhook_data.get("action") != "published":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Not a published release, ignoring"}
        )
    
    # Extract release and repository information
    release = webhook_data.get("release", {})
    repository = webhook_data.get("repository", {})
    
    tag_name = release.get("tag_name")
    repo_name = repository.get("name")
    repo_owner = repository.get("owner", {}).get("login")
    
    if not all([tag_name, repo_name, repo_owner]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required webhook data"
        )
    
    try:
        # Generate release notes
        generator = ReleaseNotesGenerator(
            prompt_path=Path("prompt.txt"),
            github_token=config["GH_TOKEN"],
            openai_model=config["OPENAI_MODEL"],
            openai_api_key=config["OPENAI_API_KEY"],
            exclude_change_types=get_config_set("EXCLUDE_PR_TYPES"),
            exclude_change_labels=get_config_set("EXCLUDE_PR_LABELS"),
            exclude_authors=get_config_set("EXCLUDE_AUTHORS"),
            db_type=config["DB_TYPE"],
            ui=None,  # No UI for webhook
            max_patch_size=int(config["MAX_PATCH_SIZE"]),
            use_db=True,
        )
        
        generator.initialize_repository(repo_owner, repo_name)
        notes = generator.generate(tag_name)
        
        # Update the release notes on GitHub
        generator.update_on_github(notes, tag_name)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Release notes generated and updated successfully",
                "tag": tag_name,
                "repository": f"{repo_owner}/{repo_name}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating release notes: {str(e)}"
        )


@cli_app.command()
def main(
	repo: str,
	tag: str,
	owner: str | None = None,
	database: bool = True,
	prompt_path: Path | None = None,
):
	cli = CLI()
	generator = ReleaseNotesGenerator(
		prompt_path=prompt_path or Path("prompt.txt"),
		github_token=config["GH_TOKEN"],
		openai_model=config["OPENAI_MODEL"],
		openai_api_key=config["OPENAI_API_KEY"],
		exclude_change_types=get_config_set("EXCLUDE_PR_TYPES"),
		exclude_change_labels=get_config_set("EXCLUDE_PR_LABELS"),
		exclude_authors=get_config_set("EXCLUDE_AUTHORS"),
		db_type=config["DB_TYPE"],
		ui=cli,
		max_patch_size=int(config["MAX_PATCH_SIZE"]),
		use_db=database,
	)
	generator.initialize_repository(owner or config["DEFAULT_OWNER"], repo)
	notes = generator.generate(tag)
	cli.show_release_notes("New Release Notes", notes)

	if cli.confirm_update():
		generator.update_on_github(notes, tag)


def get_config_set(key: str) -> set[str]:
	return set(config[key].split(",")) if config[key] else set()


if __name__ == "__main__":
	cli_app()
