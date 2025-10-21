"""Tests for the Web API endpoints."""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pretty_release_notes.web.app import app


@pytest.fixture
def client():
	"""Create a test client for the FastAPI app."""
	return TestClient(app)


@pytest.fixture
def mock_generator():
	"""Mock the ReleaseNotesGenerator to avoid actual API calls."""
	with patch("pretty_release_notes.web.app.ReleaseNotesBuilder") as mock_builder_class:
		# Create mock client
		mock_client = MagicMock()
		mock_client.generate_release_notes.return_value = "## What's Changed\n* Test PR by @test-user\n"

		# Create mock builder instance
		mock_builder = MagicMock()
		mock_builder.with_github_token.return_value = mock_builder
		mock_builder.with_openai.return_value = mock_builder
		mock_builder.with_filters.return_value = mock_builder
		mock_builder.with_progress_reporter.return_value = mock_builder
		mock_builder.build.return_value = mock_client

		# Make builder class return builder instance
		mock_builder_class.return_value = mock_builder

		yield mock_builder_class


class TestHealthEndpoint:
	"""Tests for the health check endpoint."""

	def test_health_check_returns_200(self, client):
		"""Health endpoint should return 200 OK."""
		response = client.get("/health")
		assert response.status_code == 200

	def test_health_check_returns_healthy_status(self, client):
		"""Health endpoint should return healthy status."""
		response = client.get("/health")
		assert response.json() == {"status": "healthy"}


class TestGenerateEndpoint:
	"""Tests for the /generate endpoint."""

	def test_generate_creates_job(self, client, mock_generator):
		"""Generate endpoint should create a new job."""
		response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)

		assert response.status_code == 200
		data = response.json()
		assert "job_id" in data
		assert data["status"] == "pending"
		assert "created_at" in data

	def test_generate_requires_owner(self, client):
		"""Generate endpoint should require owner field."""
		response = client.post(
			"/generate",
			json={
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)

		assert response.status_code == 422  # Unprocessable Entity

	def test_generate_requires_repo(self, client):
		"""Generate endpoint should require repo field."""
		response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)

		assert response.status_code == 422

	def test_generate_requires_tag(self, client):
		"""Generate endpoint should require tag field."""
		response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)

		assert response.status_code == 422

	def test_generate_requires_github_token(self, client):
		"""Generate endpoint should require github_token field."""
		response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"openai_key": "test-key",
			},
		)

		assert response.status_code == 422

	def test_generate_requires_openai_key(self, client):
		"""Generate endpoint should require openai_key field."""
		response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
			},
		)

		assert response.status_code == 422

	def test_generate_accepts_optional_parameters(self, client, mock_generator):
		"""Generate endpoint should accept optional configuration parameters."""
		response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
				"openai_model": "gpt-4",
				"exclude_types": ["chore", "ci"],
				"exclude_labels": ["skip-release-notes"],
				"exclude_authors": ["bot[bot]"],
			},
		)

		assert response.status_code == 200
		data = response.json()
		assert data["status"] == "pending"


class TestJobsEndpoint:
	"""Tests for the /jobs/{job_id} endpoint."""

	def test_jobs_returns_404_for_nonexistent_job(self, client):
		"""Jobs endpoint should return 404 for non-existent job ID."""
		response = client.get("/jobs/nonexistent-job-id")
		assert response.status_code == 404

	def test_jobs_returns_job_status(self, client, mock_generator):
		"""Jobs endpoint should return job status for existing jobs."""
		# Create a job first
		create_response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)
		job_id = create_response.json()["job_id"]

		# Check job status
		status_response = client.get(f"/jobs/{job_id}")
		assert status_response.status_code == 200
		data = status_response.json()
		assert data["job_id"] == job_id
		assert data["status"] in ("pending", "running", "completed", "failed")

	def test_job_completes_successfully(self, client, mock_generator):
		"""Job should eventually complete successfully."""
		# Create a job
		create_response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)
		job_id = create_response.json()["job_id"]

		# Poll for completion (with timeout)
		max_attempts = 20
		for _ in range(max_attempts):
			status_response = client.get(f"/jobs/{job_id}")
			data = status_response.json()

			if data["status"] == "completed":
				assert data["result"] is not None
				assert isinstance(data["progress"], list)  # Progress should be a list (may be empty with mock)
				assert data["error"] is None
				return

			if data["status"] == "failed":
				pytest.fail(f"Job failed with error: {data['error']}")

			time.sleep(0.1)

		pytest.fail("Job did not complete within timeout")

	def test_job_captures_progress_events(self, client, mock_generator):
		"""Job should capture progress events."""
		# Create a job
		create_response = client.post(
			"/generate",
			json={
				"owner": "test-owner",
				"repo": "test-repo",
				"tag": "v1.0.0",
				"github_token": "test-token",
				"openai_key": "test-key",
			},
		)
		job_id = create_response.json()["job_id"]

		# Wait for completion
		time.sleep(0.5)

		# Check that progress events were captured
		status_response = client.get(f"/jobs/{job_id}")
		data = status_response.json()

		# Progress should be a list (may be empty if job just started)
		assert isinstance(data["progress"], list)


class TestConcurrentRequests:
	"""Tests for concurrent API requests."""

	def test_concurrent_jobs_do_not_interfere(self, client, mock_generator):
		"""Multiple concurrent jobs should complete independently."""
		num_jobs = 3

		def create_and_wait_for_job(job_num):
			# Create job
			response = client.post(
				"/generate",
				json={
					"owner": f"owner-{job_num}",
					"repo": f"repo-{job_num}",
					"tag": "v1.0.0",
					"github_token": "test-token",
					"openai_key": "test-key",
				},
			)
			job_id = response.json()["job_id"]

			# Wait for completion
			max_attempts = 20
			for _ in range(max_attempts):
				status_response = client.get(f"/jobs/{job_id}")
				data = status_response.json()

				if data["status"] in ("completed", "failed"):
					return {
						"job_num": job_num,
						"job_id": job_id,
						"status": data["status"],
						"has_result": data["result"] is not None,
					}

				time.sleep(0.1)

			return {"job_num": job_num, "job_id": job_id, "status": "timeout"}

		# Run jobs concurrently
		with ThreadPoolExecutor(max_workers=num_jobs) as executor:
			results = list(executor.map(create_and_wait_for_job, range(num_jobs)))

		# Verify all jobs completed successfully
		assert len(results) == num_jobs
		for result in results:
			assert result["status"] == "completed", f"Job {result['job_num']} failed"
			assert result["has_result"], f"Job {result['job_num']} has no result"

	def test_concurrent_jobs_have_unique_ids(self, client, mock_generator):
		"""Concurrent jobs should have unique job IDs."""

		def create_job(job_num):
			response = client.post(
				"/generate",
				json={
					"owner": f"owner-{job_num}",
					"repo": f"repo-{job_num}",
					"tag": "v1.0.0",
					"github_token": "test-token",
					"openai_key": "test-key",
				},
			)
			return response.json()["job_id"]

		# Create jobs concurrently
		with ThreadPoolExecutor(max_workers=5) as executor:
			job_ids = list(executor.map(create_job, range(5)))

		# All job IDs should be unique
		assert len(job_ids) == len(set(job_ids))


class TestErrorHandling:
	"""Tests for error handling in the API."""

	def test_invalid_json_returns_422(self, client):
		"""Invalid JSON should return 422 Unprocessable Entity."""
		response = client.post(
			"/generate",
			data="invalid json",
			headers={"Content-Type": "application/json"},
		)
		assert response.status_code == 422

	def test_job_with_invalid_credentials_fails_gracefully(self, client):
		"""Job with invalid credentials should fail with proper error message."""
		# Create job with invalid credentials (no mock)
		response = client.post(
			"/generate",
			json={
				"owner": "nonexistent-owner",
				"repo": "nonexistent-repo",
				"tag": "v1.0.0",
				"github_token": "invalid-token",
				"openai_key": "invalid-key",
			},
		)
		job_id = response.json()["job_id"]

		# Wait for job to fail
		max_attempts = 20
		for _ in range(max_attempts):
			status_response = client.get(f"/jobs/{job_id}")
			data = status_response.json()

			if data["status"] == "failed":
				assert data["error"] is not None
				assert isinstance(data["error"], str)
				return

			if data["status"] == "completed":
				pytest.fail("Job should have failed with invalid credentials")

			time.sleep(0.1)

		pytest.fail("Job did not fail within timeout")


class TestOpenAPIDocumentation:
	"""Tests for OpenAPI documentation availability."""

	def test_openapi_json_available(self, client):
		"""OpenAPI schema should be available at /openapi.json."""
		response = client.get("/openapi.json")
		assert response.status_code == 200
		schema = response.json()
		assert "openapi" in schema
		assert "paths" in schema

	def test_docs_page_available(self, client):
		"""Interactive documentation should be available at /docs."""
		response = client.get("/docs")
		assert response.status_code == 200
		assert b"swagger-ui" in response.content.lower()
