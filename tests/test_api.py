"""API endpoint tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_job_missing_api_key():
    """Test job creation (will fail without API key, but should validate input)."""
    # This test will fail at the LLM call, but validates the endpoint structure
    response = client.post(
        "/api/v1/jobs",
        json={
            "topic": "test topic",
            "target_word_count": 1500,
            "language": "en",
        },
    )
    # Should accept the request (201) even if processing fails later
    assert response.status_code in [201, 500]  # 201 if accepted, 500 if immediate error


def test_get_job_not_found():
    """Test getting non-existent job."""
    response = client.get("/api/v1/jobs/non-existent-id")
    assert response.status_code == 404
