from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.prompts import PROMPT_TEMPLATE
from app.schemas import CommentaryRequest

client = TestClient(app)

PAYLOAD: Dict[str, Any] = {
    "program_code": "malaria-diagnostic",
    "program_name": "Malaria Rapid Diagnostic Tests",
    "event_name": "TE-2026-02",
    "overall_pass_rate": 92.0,
    "analytes": [
        {
            "name": "Malaria RDT",
            "is_quantitative": False,
            "review_comment": "Sample C had several false negatives",
            "samples": [
                {
                    "name": "Sample A",
                    "assigned_value": "Positive",
                    "participants": 40,
                    "acceptable": 36,
                    "not_acceptable": 4,
                    "pass_rate": 90.0
                },
                {
                    "name": "Sample B",
                    "assigned_value": "Negative",
                    "participants": 40,
                    "acceptable": 38,
                    "not_acceptable": 2,
                    "pass_rate": 95.0
                }
            ]
        }
    ],
    "cohorts": [
        {
            "name": "SD BIOLINE",
            "kind": "reagent",
            "participant_count": 30,
            "acceptable_percent": 93.33
        }
    ],
    "common_failure_modes": [
        "Incubation time overrun",
        "Incorrect buffer volume"
    ],
    "history": [
        {
            "event_name": "TE-2026-01",
            "pass_rate": 87.5
        }
    ],
    "example_commentaries": [
        "<p>The average score was 90% compared to 88% in the previous event.</p>"
    ]
}

@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in mock mode, without external network calls."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

def test_health_check() -> None:
    """
    Test the health check endpoint response.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "expert-commentary-service"
    assert "gemini_api_configured" in data

def test_generate_commentary_validation_error() -> None:
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

def test_generate_commentary_success() -> None:
    """
    Without GEMINI_API_KEY the service returns a mock commentary synchronously,
    without making external network calls.
    """
    response = client.post("/api/v1/commentary/generate", json=PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "DEVELOPMENT MODE" in data["commentary_html"]
    assert "Malaria Rapid Diagnostic Tests" in data["commentary_html"]
    assert "TE-2026-02" in data["commentary_html"]
    assert "Sample A (90.0%)" in data["commentary_html"]
    assert data["usage_tokens"] == 0

def test_prompt_includes_current_stats_and_examples() -> None:
    request = CommentaryRequest(**PAYLOAD)
    prompt = PROMPT_TEMPLATE.render(**request.model_dump())

    assert "**Sample A**: 40 results, 36 acceptable, 4 not acceptable. Pass Rate: 90.0% (Assigned value: Positive)" in prompt
    assert 'Reviewer note: "Sample C had several false negatives"' in prompt
    assert "**Reagent: SD BIOLINE**: 30 graded results, 93.33% acceptable" in prompt
    assert "**TE-2026-01**: 87.5%" in prompt
    assert '<example_commentary index="1">' in prompt
    assert "compared to 88% in the previous event" in prompt

def test_prompt_without_examples_or_cohorts() -> None:
    request = CommentaryRequest(**{**PAYLOAD, "cohorts": [], "example_commentaries": []})
    prompt = PROMPT_TEMPLATE.render(**request.model_dump())

    assert "example_commentary" not in prompt
    assert "there is no cohort comparison" in prompt
