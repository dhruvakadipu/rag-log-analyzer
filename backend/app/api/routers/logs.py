import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any

from app.core.config import settings
from app.services.rag_service import rag_service
from app.store.document_store import document_store
from app.models.schemas import FileUploadResponse, FileListResponse

router = APIRouter(prefix="/logs", tags=["Logs"])

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

@router.post("/upload", response_model=FileUploadResponse)
async def upload_log(file: UploadFile = File(...)):
    """Upload a log file, process it (chunk + embed), and store in FAISS."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_extensions = {".log", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    filepath = os.path.join(LOG_DIR, file.filename)
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        result = rag_service.process_and_store(file.filename, filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

    return {
        "message": "File uploaded and processed successfully.",
        **result,
    }

@router.get("/files", response_model=FileListResponse)
def list_files():
    """List all processed log files."""
    return {"files": document_store.get_all_files()}
