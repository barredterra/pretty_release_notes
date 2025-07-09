import hashlib
import hmac
import json
import logging
import os
from pathlib import Path

from dotenv import dotenv_values
from flask import Flask, request, jsonify

from generator import ReleaseNotesGenerator

# Load environment configuration
config = dotenv_values(".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def verify_webhook_signature(payload_body, signature_header, webhook_secret):
    """Verify that the payload was sent from GitHub by validating SHA256 signature."""
    if not signature_header:
        logger.warning("No signature header found")
        return False
    
    if not webhook_secret:
        logger.warning("No webhook secret configured")
        return False
    
    # GitHub prefixes the signature with 'sha256='
    signature_parts = signature_header.split('=')
    if len(signature_parts) != 2 or signature_parts[0] != 'sha256':
        logger.warning("Invalid signature format")
        return False
    
    expected_signature = signature_parts[1]
    
    # Create HMAC signature
    mac = hmac.new(
        webhook_secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    calculated_signature = mac.hexdigest()
    
    # Use secure comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, calculated_signature)
    
    if not is_valid:
        logger.warning("Signature verification failed")
    
    return is_valid


def generate_and_update_release_notes(release_data, repository_data):
    """Generate and update release notes using the existing ReleaseNotesGenerator."""
    try:
        # Extract repository information
        owner = repository_data['owner']['login']
        repo_name = repository_data['name']
        tag = release_data['tag_name']
        
        logger.info(f"Processing release {tag} for {owner}/{repo_name}")
        
        # Initialize the generator with existing configuration
        generator = ReleaseNotesGenerator(
            prompt_path=Path(config.get("PROMPT_PATH", "prompt.txt")),
            github_token=config["GH_TOKEN"],
            openai_model=config["OPENAI_MODEL"],
            openai_api_key=config["OPENAI_API_KEY"],
            exclude_change_types=get_config_set("EXCLUDE_PR_TYPES"),
            exclude_change_labels=get_config_set("EXCLUDE_PR_LABELS"),
            exclude_authors=get_config_set("EXCLUDE_AUTHORS"),
            db_type=config.get("DB_TYPE", "sqlite"),
            ui=None,  # No UI for webhook processing
            max_patch_size=int(config.get("MAX_PATCH_SIZE", "10000")),
            use_db=True,
        )
        
        # Initialize repository
        generator.initialize_repository(owner, repo_name)
        
        # Generate release notes
        notes = generator.generate(tag)
        
        # Update the release on GitHub
        generator.update_on_github(notes, tag)
        
        logger.info(f"Successfully updated release notes for {tag}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating release notes: {str(e)}")
        return False


def get_config_set(key: str) -> set[str]:
    """Helper function to parse comma-separated config values into sets."""
    return set(config[key].split(",")) if config.get(key) else set()


@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming GitHub webhook requests."""
    
    # Get headers
    event_type = request.headers.get('X-GitHub-Event')
    signature = request.headers.get('X-Hub-Signature-256')
    delivery_id = request.headers.get('X-GitHub-Delivery')
    
    logger.info(f"Received webhook: event={event_type}, delivery={delivery_id}")
    
    # Get raw payload for signature verification
    payload_body = request.get_data()
    
    # Verify webhook signature
    webhook_secret = config.get("WEBHOOK_SECRET")
    if not verify_webhook_signature(payload_body, signature, webhook_secret):
        logger.warning(f"Webhook signature verification failed for delivery {delivery_id}")
        return jsonify({"error": "Signature verification failed"}), 401
    
    # Parse JSON payload
    try:
        payload = request.get_json()
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {str(e)}")
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    # Handle release events
    if event_type == 'release':
        action = payload.get('action')
        
        # Only process when a release is published
        if action == 'published':
            release_data = payload.get('release')
            repository_data = payload.get('repository')
            
            if not release_data or not repository_data:
                logger.error("Missing release or repository data in payload")
                return jsonify({"error": "Missing release or repository data"}), 400
            
            # Process the release asynchronously in a real deployment
            # For now, we'll process it synchronously
            success = generate_and_update_release_notes(release_data, repository_data)
            
            if success:
                return jsonify({"message": "Release notes updated successfully"}), 200
            else:
                return jsonify({"error": "Failed to update release notes"}), 500
        else:
            logger.info(f"Ignoring release action: {action}")
            return jsonify({"message": f"Action '{action}' ignored"}), 200
    
    else:
        logger.info(f"Ignoring event type: {event_type}")
        return jsonify({"message": f"Event type '{event_type}' ignored"}), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "Webhook server is running"}), 200


@app.route('/', methods=['GET'])
def index():
    """Simple index page."""
    return jsonify({
        "service": "GitHub Release Notes Webhook",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        }
    }), 200


if __name__ == '__main__':
    # Check required environment variables
    required_vars = ["GH_TOKEN", "OPENAI_API_KEY", "OPENAI_MODEL"]
    missing_vars = [var for var in required_vars if not config.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    # Optional but recommended webhook secret
    if not config.get("WEBHOOK_SECRET"):
        logger.warning("WEBHOOK_SECRET not set - webhook signatures will not be verified")
    
    # Start the Flask server
    port = int(config.get("PORT", "5000"))
    debug = config.get("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)