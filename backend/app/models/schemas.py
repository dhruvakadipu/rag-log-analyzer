from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AskRequest(BaseModel):
    question: str
    filename: str
    mode: Optional[str] = None

class SummarizeRequest(BaseModel):
    filename: str
    mode: Optional[str] = None

class CompareRequest(BaseModel):
    filename1: str
    filename2: str
    mode: Optional[str] = None

class FileUploadResponse(BaseModel):
    message: str
    filename: str
    chunk_count: int
    stats: Dict[str, Any]

class FileItem(BaseModel):
    filename: str
    stats: Dict[str, Any]
    chunk_count: int

class FileListResponse(BaseModel):
    files: List[FileItem]

class HealthResponse(BaseModel):
    status: str
    ollama: Dict[str, Any]
    gemini_ready: bool
    files_loaded: int
