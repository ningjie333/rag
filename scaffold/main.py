"""
Vercel Serverless Function - FastAPI entrypoint
Proxies requests to backend FastAPI app
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from main import app

handler = app  # Vercel ASGI handler