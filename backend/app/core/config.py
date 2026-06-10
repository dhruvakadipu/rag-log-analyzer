from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Application Settings
    default_ai_mode: str = "cloud"
    log_level: str = "INFO"
    system_prompt: str = (
        "You are a highly skilled systems debugging assistant. "
        "Analyze logs carefully and provide precise, technical, and actionable insights. "
        "Focus on identifying root causes, anomalies, and performance issues. "
        "Avoid generic responses."
    )

    # Ollama Settings
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma:2b"

    # Gemini Settings
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-flash-latest"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_cooldown: int = 3

    # Local Embedding Settings
    local_embedding_model: str = "all-MiniLM-L6-v2"

    # RAG Parameters
    chunk_size: int = 200
    top_k: int = 5

    # Server Settings
    port: int = 8000
    frontend_url: str = "http://localhost:5173"
    max_log_size_mb: int = 5
    log_backup_count: int = 5
    
    # Environment
    environment: str = "local"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
