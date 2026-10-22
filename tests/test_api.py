from types import SimpleNamespace
from typing import Any, Dict, List

import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from app import services
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
    """Run every test in mock mode with no token check unless a test sets one."""
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT", "SERVICE_TOKEN"):
        monkeypatch.delenv(name, raising=False)

def test_health_check() -> None:
    """
    Test the health check endpoint response.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "expert-commentary-service"
    assert data["llm_api_key_configured"] is False

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
    Without LLM_API_KEY the service returns a mock commentary synchronously,
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

def test_generate_commentary_requires_token_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE_TOKEN", "s3cret")

    missing = client.post("/api/v1/commentary/generate", json=PAYLOAD)
    wrong = client.post("/api/v1/commentary/generate", json=PAYLOAD, headers={"X-Service-Token": "nope"})
    right = client.post("/api/v1/commentary/generate", json=PAYLOAD, headers={"X-Service-Token": "s3cret"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert right.status_code == 200

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

def test_config_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://dashscope.example.com/compatible-mode/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen3.8-max")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_TIMEOUT", "60")

    config = services.get_llm_config()

    assert config == services.LLMConfig(
        base_url="https://dashscope.example.com/compatible-mode/v1", model="qwen3.8-max", api_key="sk-test", timeout=60.0
    )
    assert config.provider == "dashscope.example.com"
    assert client.get("/health").json()["llm_model"] == "qwen3.8-max"

@pytest.mark.parametrize(
    "env, message",
    [
        ({"LLM_API_KEY": "sk-test", "LLM_MODEL": "deepseek-flash"}, "LLM_API_KEY is set but LLM_BASE_URL is not."),
        ({"LLM_API_KEY": "sk-test"}, "LLM_API_KEY is set but LLM_BASE_URL and LLM_MODEL are not."),
    ],
)
def test_misconfiguration_is_reported(monkeypatch: pytest.MonkeyPatch, env: Dict[str, str], message: str) -> None:
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    health = client.get("/health").json()
    generate = client.post("/api/v1/commentary/generate", json=PAYLOAD)

    assert health == {"status": "misconfigured", "service": "expert-commentary-service", "detail": message}
    assert generate.status_code == 500
    assert generate.json()["detail"] == message

class FakeCompletions:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: List[Dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

def _use_fake_llm(monkeypatch: pytest.MonkeyPatch, result: Any) -> Dict[str, Any]:
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("LLM_MODEL", "deepseek-flash")
    seen: Dict[str, Any] = {"completions": FakeCompletions(result)}

    def fake_openai(**kwargs: Any) -> Any:
        seen["client_kwargs"] = kwargs
        return SimpleNamespace(chat=SimpleNamespace(completions=seen["completions"]))

    monkeypatch.setattr(services, "OpenAI", fake_openai)
    return seen

def _completion(content: str) -> Any:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(total_tokens=1234),
    )

def test_generate_calls_the_configured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _use_fake_llm(monkeypatch, _completion("```html\n<p>Pass rate was 92%.</p>\n```"))

    response = client.post("/api/v1/commentary/generate", json=PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"commentary_html": "<p>Pass rate was 92%.</p>", "usage_tokens": 1234}
    assert seen["client_kwargs"]["base_url"] == "https://api.deepseek.com"
    assert seen["client_kwargs"]["api_key"] == "sk-test"
    [call] = seen["completions"].calls
    assert call["model"] == "deepseek-flash"
    assert [message["role"] for message in call["messages"]] == ["system", "user"]
    assert "**Sample A**: 40 results" in call["messages"][1]["content"]

def test_provider_errors_are_bad_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    error = openai.APIError("Insufficient Balance", request=httpx.Request("POST", "https://api.deepseek.com"), body=None)
    _use_fake_llm(monkeypatch, error)

    response = client.post("/api/v1/commentary/generate", json=PAYLOAD)

    assert response.status_code == 502
    assert response.json()["detail"] == "api.deepseek.com API error: Insufficient Balance"

def test_empty_completion_is_bad_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake_llm(monkeypatch, _completion("   "))

    response = client.post("/api/v1/commentary/generate", json=PAYLOAD)

    assert response.status_code == 502
    assert response.json()["detail"] == "api.deepseek.com returned an empty commentary."
