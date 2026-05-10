"""
Vercel Serverless Function - FastAPI entrypoint
"""
import sys
from pathlib import Path

# Add scaffold/backend to path
scaffold_backend = Path(__file__).parent / "scaffold" / "backend"
sys.path.insert(0, str(scaffold_backend))

from scaffold.backend.main import app

handler = app