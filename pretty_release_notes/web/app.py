"""FastAPI application for Pretty Release Notes."""

from datetime import datetime
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from ..api import ReleaseNotesBuilder
from ..core.interfaces import ProgressEvent, ProgressReporter
from ..openai_client import DEFAULT_MODEL

app = FastAPI(title="Pretty Release Notes API", version="1.0.0")

# In-memory job storage (use Redis in production)
jobs: dict[str, dict[str, Any]] = {}


class GenerateRequest(BaseModel):
	"""Request model for generating release notes."""

	model_config = ConfigDict(populate_by_name=True)

	owner: str
	repo: str
	tag: str
	github_token: str
	llm_key: str = Field(validation_alias=AliasChoices("llm_key", "openai_key"))
	llm_model: str = Field(default=DEFAULT_MODEL, validation_alias=AliasChoices("llm_model", "openai_model"))
	llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] | None = Field(
		default=None,
		validation_alias=AliasChoices(
			"llm_reasoning_effort",
			"openai_reasoning_effort",
			"reasoning_effort",
		),
	)
	exclude_types: list[str] = []
	exclude_labels: list[str] = []
	exclude_authors: list[str] = []
	previous_tag_name: str | None = None


class JobResponse(BaseModel):
	"""Response model for job status."""

	job_id: str
	status: str
	created_at: datetime
	completed_at: datetime | None = None
	result: str | None = None
	progress: list[dict[str, Any]] = []
	error: str | None = None


class WebProgressReporter(ProgressReporter):
	"""Store progress events for web clients."""

	def __init__(self, job_id: str):
		self.job_id = job_id
		self.events: list[dict[str, Any]] = []

	def report(self, event: ProgressEvent) -> None:
		"""Report a progress event."""
		self.events.append(
			{
				"timestamp": datetime.now().isoformat(),
				"type": event.type,
				"message": event.message,
				"metadata": event.metadata,
			}
		)
		# Update job progress
		if self.job_id in jobs:
			jobs[self.job_id]["progress"] = self.events


@app.post("/generate", response_model=JobResponse)
async def generate_release_notes(
	request: GenerateRequest,
	background_tasks: BackgroundTasks,
) -> JobResponse:
	"""Start release notes generation job."""
	import uuid

	job_id = str(uuid.uuid4())

	# Create job record
	jobs[job_id] = {
		"id": job_id,
		"status": "pending",
		"created_at": datetime.now(),
		"request": request.model_dump(),
		"progress": [],
		"result": None,
		"error": None,
	}

	# Start background task
	background_tasks.add_task(
		process_generation,
		job_id,
		request,
	)

	return JobResponse(
		job_id=job_id,
		status="pending",
		created_at=jobs[job_id]["created_at"],
		progress=[],
	)


async def process_generation(job_id: str, request: GenerateRequest) -> None:
	"""Process generation in background."""
	jobs[job_id]["status"] = "running"

	try:
		# Build client
		progress_reporter = WebProgressReporter(job_id)
		client = (
			ReleaseNotesBuilder()
			.with_github_token(request.github_token)
			.with_llm(
				request.llm_key,
				request.llm_model,
				reasoning_effort=request.llm_reasoning_effort,
			)
			.with_filters(
				exclude_types=set(request.exclude_types),
				exclude_labels=set(request.exclude_labels),
				exclude_authors=set(request.exclude_authors),
			)
			.with_progress_reporter(progress_reporter)
			.build()
		)

		# Generate notes
		result = client.generate_release_notes(
			request.owner,
			request.repo,
			request.tag,
			previous_tag_name=request.previous_tag_name,
		)

		# Update job
		jobs[job_id].update(
			{
				"status": "completed",
				"completed_at": datetime.now(),
				"result": result,
			}
		)

	except Exception as e:
		jobs[job_id].update(
			{
				"status": "failed",
				"completed_at": datetime.now(),
				"error": str(e),
			}
		)


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str) -> JobResponse:
	"""Get job status and result."""
	if job_id not in jobs:
		raise HTTPException(status_code=404, detail="Job not found")

	job = jobs[job_id]
	return JobResponse(
		job_id=job_id,
		status=job["status"],
		created_at=job["created_at"],
		completed_at=job.get("completed_at"),
		result=job.get("result"),
		progress=job.get("progress", []),
		error=job.get("error"),
	)


@app.get("/health")
async def health_check() -> dict[str, str]:
	"""Health check endpoint."""
	return {"status": "healthy"}
