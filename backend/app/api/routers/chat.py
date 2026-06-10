from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import AskRequest, SummarizeRequest, CompareRequest
from app.services.rag_service import rag_service

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/ask")
async def ask_question(request: AskRequest):
    """Ask a question about an uploaded log file using RAG."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")

    logger.info(f"Question for {request.filename} (mode={request.mode}): {request.question}")
    
    return StreamingResponse(
        rag_service.query_stream(request.filename, request.question, mode=request.mode),
        media_type="text/event-stream"
    )

@router.post("/summarize")
async def summarize_log(request: SummarizeRequest):
    """Generate a summary of an uploaded log file."""
    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")

    logger.info(f"Summarize request for {request.filename} (mode={request.mode})")
    
    return StreamingResponse(
        rag_service.summarize_stream(request.filename, mode=request.mode),
        media_type="text/event-stream"
    )

@router.post("/compare")
async def compare_logs(request: CompareRequest):
    """Compare two uploaded log files."""
    if not request.filename1.strip() or not request.filename2.strip():
        raise HTTPException(status_code=400, detail="Both filenames are required.")
    if request.filename1 == request.filename2:
        raise HTTPException(status_code=400, detail="Please select two different files to compare.")

    logger.info(f"Compare request: {request.filename1} vs {request.filename2} (mode={request.mode})")
    
    return StreamingResponse(
        rag_service.compare_stream(request.filename1, request.filename2, mode=request.mode),
        media_type="text/event-stream"
    )
