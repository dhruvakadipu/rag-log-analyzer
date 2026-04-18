import os
from dotenv import load_dotenv

load_dotenv()

# --- Application Settings ---
DEFAULT_AI_MODE = os.getenv("DEFAULT_AI_MODE", "cloud")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", (
    "You are a highly skilled systems debugging assistant. "
    "Analyze logs carefully and provide precise, technical, and actionable insights. "
    "Focus on identifying root causes, anomalies, and performance issues. "
    "Avoid generic responses."
))

# --- Model Settings ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

# Gemini Settings
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_COOLDOWN = int(os.getenv("GEMINI_COOLDOWN", "3"))

# Local Embedding Settings
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- RAG Parameters ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
TOP_K = int(os.getenv("TOP_K", "5"))

# --- Server Settings ---
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "5"))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
