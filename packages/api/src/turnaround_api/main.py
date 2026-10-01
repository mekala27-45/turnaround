"""ASGI entry point: `uvicorn turnaround_api.main:app`."""

from turnaround_api.app import create_app

app = create_app()
