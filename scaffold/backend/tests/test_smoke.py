"""Smoke tests for backend API endpoints."""
import io
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    """Test GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_get_books_endpoint():
    """Test GET /api/books returns 200 and a list."""
    response = client.get("/api/books")
    assert response.status_code == 200
    data = response.json()
    assert "books" in data
    assert isinstance(data["books"], list)


def test_upload_endpoint_with_txt_file():
    """Test POST /api/upload with a small txt file upload."""
    file_content = b"Hello, this is a test file."
    file_name = "test_upload.txt"

    response = client.post(
        "/api/upload",
        files={"file": (file_name, io.BytesIO(file_content), "text/plain")},
        data={"book_title": "TestBook_Smoke"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["chunks"] > 0
    assert "message" in data
    assert data["book_title"] == "TestBook_Smoke"
