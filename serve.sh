#!/usr/bin/env bash
# Simple wrapper to launch the FastAPI server.

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload