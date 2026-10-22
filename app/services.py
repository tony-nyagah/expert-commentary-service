import os
import logging
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.schemas import CommentaryRequest, CommentaryResponse
from app.prompts import SYSTEM_INSTRUCTIONS, PROMPT_TEMPLATE

LOGGER = logging.getLogger(__name__)

# Base directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMS_CONFIG_DIR = os.path.join(BASE_DIR, "config", "programs")

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
            with open(file_path, "r", encoding="utf-8") as f:
                LOGGER.info(f"Loaded program description from {file_path}")
                return f.read().strip()
        except Exception as e:
            LOGGER.error(f"Failed to read program description file {file_path}: {e}")
            
    LOGGER.warning(f"No local program description found for code '{program_code}' at {file_path}")
    return "No specific clinical guidelines available for this program."

def get_genai_client() -> genai.Client:
    """
    Initializes and returns the Google GenAI client.
    Reads GEMINI_API_KEY from environment variables.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        LOGGER.warning("GEMINI_API_KEY environment variable not set. Gemini client initialized in unauthenticated mode.")
        return genai.Client()
    return genai.Client(api_key=api_key)

def generate_expert_commentary(request: CommentaryRequest) -> CommentaryResponse:
    """
    Orchestrates the prompt compilation and calls Google Gemini to generate the expert EQA commentary.
    """
    # 1. Resolve program description
    description = request.program_description
    if not description:
        description = load_program_description(request.program_code)
        
    # 2. Render prompt template
    prompt_data = request.model_dump()
    prompt_data["program_description"] = description
    compiled_prompt = PROMPT_TEMPLATE.render(**prompt_data)
    
    # 3. Check for API key and handle mock mode if missing (useful for offline/initial open-source development)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        LOGGER.warning("Generating mock commentary because GEMINI_API_KEY is not set.")
        mock_html = f"""
        <h3>[DEVELOPMENT MODE - GEMINI_API_KEY IS NOT SET]</h3>
        <p>This is a mock expert commentary for the <strong>{request.program_name}</strong> program during the <strong>{request.event_name}</strong> cycle.</p>
        <p>Overall pass rate was {request.overall_pass_rate}%. Performance by sample: {', '.join([f'{a.name} {s.name} ({s.pass_rate}%)' for a in request.analytes for s in a.samples])}.</p>
        <p>Failure modes addressed: {', '.join(request.common_failure_modes) if request.common_failure_modes else 'None'}.</p>
        <p><em>Disclaimer: Please set the GEMINI_API_KEY environment variable to generate real AI commentary.</em></p>
        """
        return CommentaryResponse(commentary_html=mock_html.strip(), usage_tokens=0)
        
    # 4. Query Gemini API
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    client = get_genai_client()
    
    try:
        LOGGER.info(f"Querying model '{model_name}' for EQA program '{request.program_code}'...")
        response = client.models.generate_content(
            model=model_name,
            contents=compiled_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS,
                temperature=0.2, # Low temperature for consistent, analytical clinical output
            )
        )
        
        commentary_text = response.text
        if not commentary_text:
            raise ValueError("Empty response text returned from Gemini API.")
            
        # Extract token usage metadata if available
        usage_tokens = None
        if response.usage_metadata:
            usage_tokens = response.usage_metadata.total_token_count
            
        return CommentaryResponse(
            commentary_html=commentary_text.strip(),
            usage_tokens=usage_tokens
        )
        
    except APIError as e:
        LOGGER.error(f"Gemini API call failed: {e}")
        raise RuntimeError(f"Gemini API Error: {e.message}") from e
    except Exception as e:
        LOGGER.error(f"Unexpected error during commentary generation: {e}")
        raise RuntimeError(f"Generation failed: {str(e)}") from e
