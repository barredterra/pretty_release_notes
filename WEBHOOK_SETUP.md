# GitHub Webhook Setup Guide

This guide will help you set up the GitHub webhook receiver system to automatically generate AI-powered release notes when a release is published.

## 🎯 What This System Does

When you publish a release on GitHub, the webhook system:
1. **Receives** the webhook event from GitHub
2. **Verifies** the webhook signature for security
3. **Extracts** release and repository information
4. **Generates** AI-powered release notes using your existing generator
5. **Updates** the GitHub release with improved notes

## 🚀 Quick Start

### 1. Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# GitHub Configuration
GH_TOKEN=ghp_your_github_token_here
DEFAULT_OWNER=your_github_username

# OpenAI Configuration  
OPENAI_API_KEY=sk-your_openai_key_here
OPENAI_MODEL=gpt-4o

# Webhook Configuration
WEBHOOK_SECRET=your_secure_random_string_here
PORT=5000
DEBUG=false
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Webhook Server

```bash
python webhook_server.py
```

You should see:
```
2024-01-01 12:00:00,000 - INFO - Starting webhook server on port 5000
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://[::1]:5000
```

### 4. Configure GitHub Webhook

In your GitHub repository:

1. Go to **Settings** → **Webhooks**
2. Click **Add webhook**
3. Set **Payload URL**: `https://your-domain.com/webhook`
4. Set **Content type**: `application/json`
5. Set **Secret**: (same value as `WEBHOOK_SECRET` in your `.env`)
6. Select **Let me select individual events**
7. Check only **Releases**
8. Ensure **Active** is checked
9. Click **Add webhook**

## 🔧 Configuration Details

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GH_TOKEN` | GitHub personal access token with repo permissions | `ghp_abc123...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-abc123...` |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_SECRET` | - | Secret for webhook signature verification (recommended) |
| `PORT` | `5000` | Port for the webhook server |
| `DEBUG` | `false` | Enable Flask debug mode |
| `PROMPT_PATH` | `prompt.txt` | Path to the prompt template |
| `MAX_PATCH_SIZE` | `10000` | Maximum patch size for analysis |
| `DB_TYPE` | `sqlite` | Database type (`sqlite` or `csv`) |
| `EXCLUDE_PR_TYPES` | - | Comma-separated PR types to exclude (e.g., `chore,ci,refactor`) |
| `EXCLUDE_PR_LABELS` | - | Comma-separated labels to exclude |
| `EXCLUDE_AUTHORS` | - | Comma-separated authors to exclude (e.g., `dependabot,renovate`) |

### GitHub Token Permissions

Your GitHub token needs these permissions:
- `Contents`: Read (to access repository contents)
- `Metadata`: Read (to access repository metadata)
- `Pull requests`: Read (to analyze PR information)
- `Actions`: Read (if analyzing workflow-related PRs)

For GitHub Apps, ensure you have:
- Repository permissions: `Contents` (read), `Metadata` (read), `Pull requests` (read)

## 🧪 Testing

### Test the Server Locally

Use the provided test script:

```bash
python webhook_test.py
```

This will:
- Check if the server is running (`/health` endpoint)
- Send test webhook payloads
- Verify signature handling
- Test different release actions

### Test Individual Endpoints

```bash
# Health check
curl http://localhost:5000/health

# Service info
curl http://localhost:5000/
```

### Simulate a Release Webhook

Create a test payload file:

```json
{
  "action": "published",
  "release": {
    "tag_name": "v1.0.0",
    "name": "Test Release",
    "body": "Initial release"
  },
  "repository": {
    "name": "test-repo", 
    "full_name": "owner/test-repo",
    "owner": {
      "login": "owner"
    }
  }
}
```

Send it with curl:

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: release" \
  -H "X-GitHub-Delivery: 12345" \
  -d @test_payload.json
```

## 🚀 Production Deployment

### Using Docker

Build and run with Docker:

```bash
# Build the image
docker build -t release-notes-webhook .

# Run the container
docker run -d \
  --name release-notes-webhook \
  -p 5000:5000 \
  --env-file .env \
  release-notes-webhook
```

### Using Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service  
docker-compose down
```

### Manual Deployment

For a production deployment on a server:

1. **Use a reverse proxy** (nginx, Apache) for SSL termination
2. **Set up a process manager** (systemd, supervisor) to keep the service running
3. **Configure monitoring** for the `/health` endpoint
4. **Set up log rotation** and monitoring

Example systemd service file (`/etc/systemd/system/release-notes-webhook.service`):

```ini
[Unit]
Description=GitHub Release Notes Webhook
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/release-notes-webhook
Environment=PATH=/opt/release-notes-webhook/env/bin
ExecStart=/opt/release-notes-webhook/env/bin/python webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Example nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /webhook {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Webhook-specific settings
        proxy_buffering off;
        proxy_request_buffering off;
        client_max_body_size 25m;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:5000;
        access_log off;
    }
}
```

## 🔒 Security Considerations

### Webhook Secret

Always configure `WEBHOOK_SECRET`:
- Use a long, random string (32+ characters)
- Store it securely (environment variable, secrets manager)
- Never commit it to version control

Generate a secure secret:
```bash
# Using openssl
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Network Security

- **Use HTTPS** in production to encrypt webhook payloads
- **Restrict access** to the webhook endpoint (firewall, VPN)
- **Monitor** webhook requests for suspicious activity

### GitHub Token Security

- Use **minimal permissions** required for the task
- Consider using a **GitHub App** instead of personal access tokens
- **Rotate tokens** regularly
- **Monitor token usage** in GitHub settings

## 📊 Monitoring and Logging

### Health Monitoring

Monitor the `/health` endpoint:

```bash
# Simple monitoring script
while true; do
  if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "$(date): Service is healthy"
  else
    echo "$(date): Service is down!"
    # Add alerting logic here
  fi
  sleep 60
done
```

### Log Analysis

The webhook server logs important events:

```bash
# View recent logs
tail -f /var/log/release-notes-webhook.log

# Monitor webhook events
grep "Received webhook" /var/log/release-notes-webhook.log

# Monitor errors
grep "ERROR" /var/log/release-notes-webhook.log
```

### Metrics to Monitor

- Webhook request rate and success rate
- Release notes generation time
- GitHub API rate limit usage
- OpenAI API usage and costs
- Server resource usage (CPU, memory)

## 🔧 Troubleshooting

### Common Issues

**Webhook not received:**
- Check GitHub webhook delivery status in repository settings
- Verify the webhook URL is accessible from GitHub
- Check firewall settings

**Signature verification failed:**
- Ensure `WEBHOOK_SECRET` matches the secret configured in GitHub
- Check that webhook content-type is `application/json`

**Release notes not updated:**
- Verify GitHub token has write permissions to the repository
- Check GitHub API rate limits
- Review server logs for specific error messages

**OpenAI API errors:**
- Check API key validity and billing status
- Monitor API rate limits and usage
- Verify the specified model is available

### Debug Mode

Enable debug mode for detailed logging:

```bash
# In .env file
DEBUG=true

# Or set environment variable
export DEBUG=true
python webhook_server.py
```

### Testing Webhook Delivery

In GitHub repository settings > Webhooks:
1. Click on your webhook
2. Scroll to "Recent Deliveries" 
3. Click on a delivery to see request/response details
4. Use "Redeliver" to test again

## 📋 Maintenance

### Regular Tasks

- **Monitor logs** for errors and performance issues
- **Review GitHub API usage** and rate limits
- **Update dependencies** regularly for security patches
- **Test webhook functionality** after deployments
- **Backup database** files (if using sqlite)

### Updates

To update the webhook system:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Restart the service
# (method depends on your deployment)
```

## 🤝 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review server logs for error messages
3. Test with the provided test script
4. Verify GitHub webhook delivery logs
5. Create an issue with detailed error information

The webhook system integrates seamlessly with your existing release notes generation infrastructure while providing automated, secure processing of GitHub release events.