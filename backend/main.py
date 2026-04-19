"""
FastAPI backend for Logly - Ask your logs anything.
"""

import os
import shutil
import logging
import json
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from logging.handlers import RotatingFileHandler
import config

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Rotate logs after 5MB, keep 5 backup files
        RotatingFileHandler(
            "backend.log", 
            maxBytes=config.MAX_LOG_SIZE_MB * 1024 * 1024, 
            backupCount=config.LOG_BACKUP_COUNT
        )
    ]
)
logger = logging.getLogger("log-copilot")
logger.info("Initializing Log Analysis Copilot Backend...")


from rag import rag_store, OllamaClient

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

import contextlib

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info("--- SYSTEM STARTUP: MODEL CHECK ---")
    
    # 1. Check Ollama
    ollama = OllamaClient()
    ollama_info = ollama.get_health_status()
    if ollama_info["online"]:
        if ollama_info["model_found"]:
            logger.info(f"[OK]  Ollama:        ONLINE (Model '{ollama_info['model_name']}' is ready)")
        else:
            logger.warning(f"[!]   Ollama:        ONLINE (But model '{ollama_info['model_name']}' is missing!)")
            logger.warning(f"      Action: Run 'ollama pull {ollama_info['model_name']}'")
    else:
        logger.warning(f"[X]   Ollama:        OFFLINE (Ensure 'ollama serve' is running at {config.OLLAMA_BASE_URL})")

    # 2. Check Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        logger.info(f"[OK]  Gemini Cloud:  READY (Model '{config.GEMINI_MODEL}')")
    else:
        logger.info(f"[-]   Gemini Cloud:  NOT CONFIGURED (Cloud mode disabled)")

    # 3. Check Embedding Model
    try:
        from embedding import EmbeddingModel
        _ = EmbeddingModel.get_instance()
        
        embed_label = "Cloud" if gemini_key else "Local"
        embed_model = config.GEMINI_EMBEDDING_MODEL if gemini_key else config.LOCAL_EMBEDDING_MODEL
        logger.info(f"[OK]  Embeddings:    READY ({embed_label} Model '{embed_model}')")
    except Exception as e:
        logger.error(f"[X]   Embeddings:    ERROR loading embeddings: {e}")
    
    logger.info("------------------------------------")
    
    yield
    # --- SHUTDOWN (Optional) ---
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

if config.FRONTEND_URL:
    origins.append(config.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure data directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str
    filename: str
    mode: str = config.DEFAULT_AI_MODE


class SummarizeRequest(BaseModel):
    filename: str
    mode: str = config.DEFAULT_AI_MODE


class CompareRequest(BaseModel):
    filename1: str
    filename2: str
    mode: str = config.DEFAULT_AI_MODE


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint to confirm API is running."""
    return {
        "message": "Log Analysis Copilot API is online",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    ollama = OllamaClient()
    ollama_info = ollama.get_health_status()
    gemini_key_set = os.getenv("GEMINI_API_KEY") is not None
    
    return {
        "status": "ok",
        "ollama": ollama_info,
        "gemini_ready": gemini_key_set,
        "files_loaded": len(rag_store.documents),
    }
    

@app.post("/upload-log")
async def upload_log(file: UploadFile = File(...)):
    """
    Upload a log file, process it (chunk + embed), and store in FAISS.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_extensions = {".log", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save file to disk
    filepath = os.path.join(LOG_DIR, file.filename)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Process: chunk, embed, index
    try:
        result = rag_store.process_and_store(file.filename, filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

    return {
        "message": "File uploaded and processed successfully.",
        **result,
    }


@app.post("/ask")
async def ask_question(request: AskRequest):
    """
    Ask a question about an uploaded log file using RAG.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")

    logger.info(f"Question for {request.filename} (mode={request.mode}): {request.question}")
    
    return StreamingResponse(
        rag_store.query_stream(request.filename, request.question, mode=request.mode),
        media_type="text/event-stream"
    )


@app.post("/summarize")
async def summarize_log(request: SummarizeRequest):
    """Generate a summary of an uploaded log file."""
    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")

    logger.info(f"Summarize request for {request.filename} (mode={request.mode})")
    
    return StreamingResponse(
        rag_store.summarize_stream(request.filename, mode=request.mode),
        media_type="text/event-stream"
    )


@app.post("/compare")
async def compare_logs(request: CompareRequest):
    """Compare two uploaded log files."""
    if not request.filename1.strip() or not request.filename2.strip():
        raise HTTPException(status_code=400, detail="Both filenames are required.")

    if request.filename1 == request.filename2:
        raise HTTPException(status_code=400, detail="Please select two different files to compare.")

    logger.info(f"Compare request: {request.filename1} vs {request.filename2} (mode={request.mode})")
    
    return StreamingResponse(
        rag_store.compare_stream(request.filename1, request.filename2, mode=request.mode),
        media_type="text/event-stream"
    )


@app.get("/files")
def list_files():
    """List all processed log files."""
    return {"files": rag_store.get_files()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, reload=False)
