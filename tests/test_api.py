import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """
    Test the health check endpoint response.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "expert-commentary-service"
    assert "gemini_api_configured" in data

def test_generate_commentary_validation_error():
    """
    Test that sending incomplete data returns a 422 Unprocessable Entity.
    """
    incomplete_payload = {
        "program_code": "MALARIA-RDT",
        "program_name": "Malaria Rapid Test EQA"
        # Missing other required fields
    }
    response = client.post("/api/v1/commentary/generate", json=incomplete_payload)
    assert response.status_code == 422

def test_generate_commentary_success(monkeypatch):
    """
    Test that the commentary generate endpoint succeeds.
    We mock the environment variable GEMINI_API_KEY to ensure it triggers the mock/offline mode
    and completes synchronously without making external network calls.
    """
    # Ensure GEMINI_API_KEY is not set for mock offline test execution
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    payload = {
        "program_code": "malaria-diagnostic",
        "program_name": "Malaria Rapid Diagnostic Tests",
        "event_name": "TE-2026-02",
        "overall_average_score": 92.5,
        "samples": [
            {
                "sample_name": "Sample A",
                "target_value": None,
                "pass_rate": 90.0,
                "average_score": 90.0
            },
            {
                "sample_name": "Sample B",
                "target_value": None,
                "pass_rate": 95.0,
                "average_score": 95.0
            }
        ],
        "cohorts": [
            {
                "method_name": "Immunochromatography",
                "participant_count": 45,
                "mean": 91.2,
                "cv": 5.4
            }
        ],
        "common_failure_modes": [
            "Incubation time overrun",
            "Incorrect buffer volume"
        ],
        "history": [
            {
                "event_name": "TE-2026-01",
                "average_score": 89.0,
                "pass_rate": 87.5
            }
        ]
    }
    
    response = client.post("/api/v1/commentary/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "commentary_html" in data
    assert "DEVELOPMENT MODE" in data["commentary_html"]
    assert "Malaria Rapid Diagnostic Tests" in data["commentary_html"]
    assert "TE-2026-02" in data["commentary_html"]
    assert data["usage_tokens"] == 0
