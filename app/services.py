import logging
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from openai import APIError, OpenAI

from app.prompts import PROMPT_TEMPLATE, SYSTEM_INSTRUCTIONS
from app.schemas import CommentaryRequest, CommentaryResponse

LOGGER = logging.getLogger(__name__)

# Base directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMS_CONFIG_DIR = os.path.join(BASE_DIR, "config", "programs")


class LLMConfigError(Exception):
    """The LLM_* environment variables don't describe a usable provider."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str | None
    model: str | None
    api_key: str | None
    timeout: float

    @property
    def provider(self) -> str:
        """Short name for logs and error messages, e.g. api.deepseek.com"""
        return (urlparse(self.base_url).hostname if self.base_url else None) or "LLM"


def get_llm_config() -> LLMConfig:
    """
    Reads the LLM to call from environment variables. Any provider with an OpenAI-compatible
    chat completions API works (DeepSeek, Qwen, Gemini, ...):

    - LLM_BASE_URL: the provider's OpenAI-compatible base URL, e.g. https://api.deepseek.com
    - LLM_MODEL: the model name, e.g. deepseek-flash
    - LLM_API_KEY: the provider's API key. Without it the service returns a placeholder commentary.
    - LLM_TIMEOUT: seconds to wait for the provider (default 110, under the platform's usual 120 s).
    """
    config = LLMConfig(
        base_url=os.getenv("LLM_BASE_URL") or None,
        model=os.getenv("LLM_MODEL") or None,
        api_key=os.getenv("LLM_API_KEY") or None,
        timeout=float(os.getenv("LLM_TIMEOUT", "110")),
    )
    if config.api_key:
        missing = [
            name for name, value in (("LLM_BASE_URL", config.base_url), ("LLM_MODEL", config.model)) if not value
        ]
        if missing:
            raise LLMConfigError(
                f"LLM_API_KEY is set but {' and '.join(missing)} {'is' if len(missing) == 1 else 'are'} not."
            )
    return config


def load_program_description(program_code: str) -> str:
    """
    Attempts to load a static program description from the config directory.
    Looks for a markdown file matching config/programs/{program_code}.md
    """
    # Normalize to lowercase and remove alphanumeric characters to prevent path traversal
    safe_code = "".join(c for c in program_code.lower() if c.isalnum() or c in "-_")
    file_path = os.path.join(PROGRAMS_CONFIG_DIR, f"{safe_code}.md")

    if os.path.exists(file_path):
        try:
            with open(file_path, encoding="utf-8") as f:
                LOGGER.info(f"Loaded program description from {file_path}")
                return f.read().strip()
        except Exception as e:
            LOGGER.error(f"Failed to read program description file {file_path}: {e}")

    LOGGER.warning(f"No local program description found for code '{program_code}' at {file_path}")
    return "No specific clinical guidelines available for this program."


# Models sometimes wrap the HTML in a markdown code block despite being told not to
_CODE_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n?\s*```\s*$", re.DOTALL)


def strip_code_fence(text: str) -> str:
    match = _CODE_FENCE_RE.match(text)
    return match.group(1) if match else text


def get_llm_client(config: LLMConfig) -> OpenAI:
    # No retries: the calling platform has its own timeout and a retry would overrun it
    return OpenAI(base_url=config.base_url, api_key=config.api_key, timeout=config.timeout, max_retries=0)


def generate_expert_commentary(request: CommentaryRequest) -> CommentaryResponse:
    """
    Orchestrates the prompt compilation and calls the configured LLM to generate the expert EQA commentary.
    """
    config = get_llm_config()

    # 1. Resolve program description
    description = request.program_description
    if not description:
        description = load_program_description(request.program_code)

    # 2. Render prompt template
    prompt_data = request.model_dump()
    prompt_data["program_description"] = description
    compiled_prompt = PROMPT_TEMPLATE.render(**prompt_data)

    # 3. Check for API key and handle mock mode if missing (useful for offline/initial open-source development)
    if not config.api_key:
        LOGGER.warning("Generating mock commentary because LLM_API_KEY is not set.")
        mock_html = f"""
        <h3>[DEVELOPMENT MODE - LLM_API_KEY IS NOT SET]</h3>
        <p>This is a mock expert commentary for the <strong>{request.program_name}</strong> program during the <strong>{request.event_name}</strong> cycle.</p>
        <p>Overall pass rate was {request.overall_pass_rate}%. Performance by sample: {", ".join([f"{a.name} {s.name} ({s.pass_rate}%)" for a in request.analytes for s in a.samples])}.</p>
        <p>Failure modes addressed: {", ".join(request.common_failure_modes) if request.common_failure_modes else "None"}.</p>
        <p><em>Disclaimer: Please set the LLM_API_KEY environment variable to generate real AI commentary.</em></p>
        """
        return CommentaryResponse(commentary_html=mock_html.strip(), usage_tokens=0)

    # 4. Query the LLM
    client = get_llm_client(config)

    try:
        LOGGER.info(f"Querying {config.provider} model '{config.model}' for EQA program '{request.program_code}'...")
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": compiled_prompt},
            ],
            temperature=0.2,  # Low temperature for consistent, analytical clinical output
        )
    except APIError as e:
        LOGGER.error(f"{config.provider} API call failed: {e}")
        raise RuntimeError(f"{config.provider} API error: {e.message}") from e
    except Exception as e:
        LOGGER.error(f"Unexpected error during commentary generation: {e}")
        raise RuntimeError(f"Generation failed: {str(e)}") from e

    commentary_text = response.choices[0].message.content if response.choices else None
    if not commentary_text or not commentary_text.strip():
        raise RuntimeError(f"{config.provider} returned an empty commentary.")

    return CommentaryResponse(
        commentary_html=strip_code_fence(commentary_text.strip()).strip(),
        usage_tokens=response.usage.total_tokens if response.usage else None,
    )
