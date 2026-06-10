from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse
from app.services.llm.providers import OllamaClient
from app.store.document_store import document_store

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    ollama = OllamaClient()
    ollama_info = ollama.get_health_status()
    gemini_key_set = bool(settings.gemini_api_key)
    
    return {
        "status": "ok",
        "ollama": ollama_info,
        "gemini_ready": gemini_key_set,
        "files_loaded": len(document_store.documents),
    }

@router.get("/")
async def root():
    """Root endpoint to confirm API is running."""
    return {
        "message": "Log Analysis Copilot API is online",
        "docs": "/docs",
        "health": "/health"
    }
