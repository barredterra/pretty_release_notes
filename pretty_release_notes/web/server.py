"""Uvicorn server runner for Pretty Release Notes API."""

import uvicorn

if __name__ == "__main__":
	uvicorn.run(
		"pretty_release_notes.web.app:app",
		host="0.0.0.0",
		port=8000,
		log_level="info",
	)
