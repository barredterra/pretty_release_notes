#!/usr/bin/env python3
"""
FastAPI server for GitHub webhook handling
"""

import uvicorn
from main import api_app

if __name__ == "__main__":
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )