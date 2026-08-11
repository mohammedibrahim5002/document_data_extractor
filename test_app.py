import pytest
from fastapi.testclient import TestClient
from app import app

# Initialize the test client with your FastAPI application
client = TestClient(app)

def test_frontend_loads():
    """
    Verify that the frontend UI (index.html) loads successfully.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"Document Data Extractor" in response.content
    assert "text/html" in response.headers["content-type"]

def test_api_extract_missing_file():
    """
    Verify that the API correctly catches and rejects requests missing a file payload.
    FastAPI should return a 422 Unprocessable Entity status.
    """
    response = client.post("/api/extract")
    assert response.status_code == 422

def test_api_extract_invalid_file_type():
    """
    Verify that the API rejects files that are not images or PDFs.
    """
    # Create a dummy text file to simulate an invalid upload
    files = {'file': ('test.txt', b'This is a fake text file.', 'text/plain')}
    
    response = client.post("/api/extract", files=files)
    
    # Depending on your exact implementation in app.py, this might be a 400 or 422.
    # We will assert that it does not return a 200 OK.
    assert response.status_code != 200