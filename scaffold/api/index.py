"""
Vercel Serverless Function - FastAPI entrypoint
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from main import app

# Vercel handler
handler = app