import os
from dotenv import load_dotenv

load_dotenv()

# --- Application Settings ---
DEFAULT_AI_MODE = os.getenv("DEFAULT_AI_MODE", "cloud")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", (
    "You are a highly skilled systems debugging assistant. "
    "Analyze logs carefully and provide precise, technical, and actionable insights. "
    "Focus on identifying root causes, anomalies, and performance issues. "
    "Avoid generic responses."
))

# --- Model Settings ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

# Gemini LLM model
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Gemini Embedding model
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
# Rate limit cooldown in seconds
GEMINI_COOLDOWN = int(os.getenv("GEMINI_COOLDOWN", "3"))

LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- RAG Parameters ---
# Number of characters per log chunk
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "200"))
# Number of top results to retrieve from FAISS
TOP_K = int(os.getenv("TOP_K", "5"))

# --- Server Settings ---
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
