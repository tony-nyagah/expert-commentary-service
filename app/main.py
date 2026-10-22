import logging
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.schemas import CommentaryRequest, CommentaryResponse
from app.services import LLMConfigError, generate_expert_commentary, get_llm_config

# Load environment variables from .env if present
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", handlers=[logging.StreamHandler()]
)
LOGGER = logging.getLogger("expert-commentary-service")

app = FastAPI(
    title="AI EQA Commentary Generator",
    version="1.0.0",
    description="A standalone clinical expert commentary generator for laboratory proficiency testing (PT) and External Quality Assessment (EQA) schemes using any OpenAI-compatible LLM (DeepSeek, Qwen, Gemini, ...).",
)

# No CORS middleware: the service is meant to be called server-to-server by the EQA platform's
# backend, never directly from a browser.


def verify_service_token(x_service_token: str | None = Header(None)) -> None:
    """
    Requires the X-Service-Token header to match SERVICE_TOKEN when SERVICE_TOKEN is set.
    Leaving SERVICE_TOKEN unset disables the check, which is only meant for local development.
    """
    expected = os.getenv("SERVICE_TOKEN")
    if not expected:
        return
    if x_service_token is None or not secrets.compare_digest(x_service_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing service token.")


@app.get("/", status_code=status.HTTP_200_OK)
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Service health check endpoint.
    """
    try:
        config = get_llm_config()
    except LLMConfigError as e:
        return {"status": "misconfigured", "service": "expert-commentary-service", "detail": str(e)}
    return {
        "status": "healthy",
        "service": "expert-commentary-service",
        "llm_base_url": config.base_url,
        "llm_model": config.model,
        "llm_api_key_configured": config.api_key is not None,
    }


@app.post(
    "/api/v1/commentary/generate",
    response_model=CommentaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate EQA expert commentary",
    description="Accepts aggregated statistics, method cohorts, failure modes, history and example commentaries, compiling them into a prompt and returning clinical expert commentary draft in HTML.",
    dependencies=[Depends(verify_service_token)],
)
def generate_commentary(request: CommentaryRequest) -> CommentaryResponse:
    try:
        LOGGER.info(
            f"Received commentary generation request for program: {request.program_code}, event: {request.event_name}"
        )
        response = generate_expert_commentary(request)
        return response
    except LLMConfigError as e:
        LOGGER.error(f"Configuration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    except ValueError as e:
        LOGGER.error(f"Validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except RuntimeError as e:
        LOGGER.error(f"Generation error: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    except Exception as e:
        LOGGER.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during commentary generation.",
        ) from e
