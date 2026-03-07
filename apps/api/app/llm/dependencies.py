from app.llm.client import BlindNavLLMClient
from app.llm.gemini_service import GeminiIntentSummaryService


def get_llm_client() -> BlindNavLLMClient:
    return GeminiIntentSummaryService()

