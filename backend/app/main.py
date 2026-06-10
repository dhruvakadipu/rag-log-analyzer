import contextlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.services.llm.providers import OllamaClient
from app.services.embeddings import EmbeddingModel
from app.api.routers import health, logs, chat

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("--- SYSTEM STARTUP: MODEL CHECK ---")
    
    ollama = OllamaClient()
    ollama_info = ollama.get_health_status()
    if ollama_info["online"]:
        if ollama_info["model_found"]:
            logger.info(f"[OK]  Ollama:        ONLINE (Model '{ollama_info['model_name']}' is ready)")
        else:
            logger.warning(f"[!]   Ollama:        ONLINE (But model '{ollama_info['model_name']}' is missing!)")
            logger.warning(f"      Action: Run 'ollama pull {ollama_info['model_name']}'")
    else:
        logger.warning(f"[X]   Ollama:        OFFLINE (Ensure 'ollama serve' is running at {settings.ollama_base_url})")

    if settings.gemini_api_key:
        logger.info(f"[OK]  Gemini Cloud:  READY (Model '{settings.gemini_model}')")
    else:
        logger.info(f"[-]   Gemini Cloud:  NOT CONFIGURED (Cloud mode disabled)")

    try:
        _ = EmbeddingModel.get_instance()
        embed_label = "Cloud" if settings.gemini_api_key else "Local"
        embed_model = settings.gemini_embedding_model if settings.gemini_api_key else settings.local_embedding_model
        logger.info(f"[OK]  Embeddings:    READY ({embed_label} Model '{embed_model}')")
    except Exception as e:
        logger.error(f"[X]   Embeddings:    ERROR loading embeddings: {e}")
    
    logger.info("------------------------------------")
    yield
    logger.info("Shutting down Logly...")


app = FastAPI(
    title="Logly",
    description="AI-powered log analysis using local LLM (Ollama) and RAG",
    version="1.0.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.frontend_url:
    origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(logs.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=False)
