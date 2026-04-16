"""
FastAPI backend for the Engineering Copilot for Log Analysis.
"""

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from rag import rag_store, OllamaClient

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Log Analysis Copilot",
    description="AI-powered log analysis using local LLM (Ollama) and RAG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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
    mode: str = "local"


class SummarizeRequest(BaseModel):
    filename: str
    mode: str = "local"


class CompareRequest(BaseModel):
    filename1: str
    filename2: str
    mode: str = "local"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Health check endpoint — also verifies Ollama connectivity."""
    ollama = OllamaClient()
    ollama_status = ollama.is_available()
    return {
        "status": "ok",
        "ollama_connected": ollama_status,
        "ollama_model": ollama.model,
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

    result = rag_store.query(request.filename, request.question, mode=request.mode)
    return result


@app.post("/summarize")
async def summarize_log(request: SummarizeRequest):
    """Generate a summary of an uploaded log file."""
    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")

    result = rag_store.summarize(request.filename, mode=request.mode)
    return result


@app.post("/compare")
async def compare_logs(request: CompareRequest):
    """Compare two uploaded log files."""
    if not request.filename1.strip() or not request.filename2.strip():
        raise HTTPException(status_code=400, detail="Both filenames are required.")

    if request.filename1 == request.filename2:
        raise HTTPException(status_code=400, detail="Please select two different files to compare.")

    result = rag_store.compare(request.filename1, request.filename2, mode=request.mode)
    return result


@app.get("/files")
def list_files():
    """List all processed log files."""
    return {"files": rag_store.get_files()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
