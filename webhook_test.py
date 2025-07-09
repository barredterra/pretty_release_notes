#!/usr/bin/env python3
"""
Test script for the GitHub webhook server.
This simulates a GitHub release webhook payload.
"""

import hashlib
import hmac
import json
import requests
import time
from datetime import datetime

# Configuration
WEBHOOK_URL = "http://localhost:5000/webhook"
WEBHOOK_SECRET = "test_secret_123"  # Should match WEBHOOK_SECRET in .env

# Sample webhook payload (GitHub release published event)
SAMPLE_PAYLOAD = {
    "action": "published",
    "release": {
        "url": "https://api.github.com/repos/test-owner/test-repo/releases/1",
        "assets_url": "https://api.github.com/repos/test-owner/test-repo/releases/1/assets",
        "upload_url": "https://uploads.github.com/repos/test-owner/test-repo/releases/1/assets{?name,label}",
        "html_url": "https://github.com/test-owner/test-repo/releases/tag/v1.0.0",
        "id": 1,
        "author": {
            "login": "test-user",
            "id": 1,
            "node_id": "MDQ6VXNlcjE=",
            "avatar_url": "https://github.com/images/error/test-user_happy.gif",
            "gravatar_id": "",
            "url": "https://api.github.com/users/test-user",
            "html_url": "https://github.com/test-user",
            "type": "User",
            "site_admin": False
        },
        "node_id": "MDc6UmVsZWFzZTE=",
        "tag_name": "v1.0.0",
        "target_commitish": "master",
        "name": "v1.0.0",
        "draft": False,
        "prerelease": False,
        "created_at": "2024-01-01T12:00:00Z",
        "published_at": "2024-01-01T12:00:00Z",
        "assets": [],
        "tarball_url": "https://api.github.com/repos/test-owner/test-repo/tarball/v1.0.0",
        "zipball_url": "https://api.github.com/repos/test-owner/test-repo/zipball/v1.0.0",
        "body": "Initial release"
    },
    "repository": {
        "id": 1,
        "node_id": "MDEwOlJlcG9zaXRvcnkx",
        "name": "test-repo",
        "full_name": "test-owner/test-repo",
        "private": False,
        "owner": {
            "login": "test-owner",
            "id": 1,
            "node_id": "MDEyOk9yZ2FuaXphdGlvbjE=",
            "avatar_url": "https://github.com/images/error/test-owner_happy.gif",
            "gravatar_id": "",
            "url": "https://api.github.com/users/test-owner",
            "html_url": "https://github.com/test-owner",
            "type": "Organization",
            "site_admin": False
        },
        "html_url": "https://github.com/test-owner/test-repo",
        "description": "Test repository",
        "fork": False,
        "url": "https://api.github.com/repos/test-owner/test-repo",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T12:00:00Z",
        "pushed_at": "2024-01-01T11:00:00Z",
        "clone_url": "https://github.com/test-owner/test-repo.git",
        "size": 0,
        "stargazers_count": 0,
        "watchers_count": 0,
        "language": "Python",
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True,
        "has_pages": False,
        "forks_count": 0,
        "archived": False,
        "disabled": False,
        "open_issues_count": 0,
        "license": None,
        "forks": 0,
        "open_issues": 0,
        "watchers": 0,
        "default_branch": "master"
    },
    "sender": {
        "login": "test-user",
        "id": 1,
        "node_id": "MDQ6VXNlcjE=",
        "avatar_url": "https://github.com/images/error/test-user_happy.gif",
        "gravatar_id": "",
        "url": "https://api.github.com/users/test-user",
        "html_url": "https://github.com/test-user",
        "type": "User",
        "site_admin": False
    }
}


def generate_signature(payload_body, secret):
    """Generate HMAC SHA256 signature for webhook verification."""
    mac = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    return f"sha256={mac.hexdigest()}"


def test_webhook(payload, secret=None):
    """Send a test webhook request."""
    
    # Convert payload to JSON
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate headers
    headers = {
        'Content-Type': 'application/json',
        'X-GitHub-Event': 'release',
        'X-GitHub-Delivery': f'12345678-1234-1234-1234-{int(time.time())}',
        'User-Agent': 'GitHub-Hookshot/test'
    }
    
    # Add signature if secret provided
    if secret:
        headers['X-Hub-Signature-256'] = generate_signature(payload_bytes, secret)
    
    print(f"Sending webhook to {WEBHOOK_URL}")
    print(f"Event: release")
    print(f"Action: {payload['action']}")
    print(f"Repository: {payload['repository']['full_name']}")
    print(f"Release: {payload['release']['tag_name']}")
    
    if secret:
        print(f"Using signature verification")
    else:
        print("No signature verification")
    
    print("-" * 50)
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=payload_bytes,
            headers=headers,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response Body: {json.dumps(response_json, indent=2)}")
        except:
            print(f"Response Body: {response.text}")
            
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False


def test_health():
    """Test the health endpoint."""
    try:
        response = requests.get(f"http://localhost:5000/health", timeout=10)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Health check failed: {e}")
        return False


def main():
    """Run webhook tests."""
    print("GitHub Webhook Server Test")
    print("=" * 50)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    if not test_health():
        print("❌ Health check failed. Is the server running?")
        return
    print("✅ Health check passed")
    
    # Test webhook without signature
    print("\n2. Testing webhook without signature...")
    if test_webhook(SAMPLE_PAYLOAD):
        print("✅ Webhook without signature succeeded")
    else:
        print("❌ Webhook without signature failed")
    
    # Test webhook with signature
    print("\n3. Testing webhook with signature...")
    if test_webhook(SAMPLE_PAYLOAD, WEBHOOK_SECRET):
        print("✅ Webhook with signature succeeded")
    else:
        print("❌ Webhook with signature failed")
    
    # Test different actions
    print("\n4. Testing different release actions...")
    
    test_actions = ["created", "edited", "deleted"]
    for action in test_actions:
        print(f"\nTesting action: {action}")
        test_payload = SAMPLE_PAYLOAD.copy()
        test_payload["action"] = action
        
        if test_webhook(test_payload, WEBHOOK_SECRET):
            print(f"✅ Action '{action}' handled correctly")
        else:
            print(f"❌ Action '{action}' failed")


if __name__ == "__main__":
    main()