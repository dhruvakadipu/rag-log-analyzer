import json
from typing import Generator

from app.core.config import settings
from app.core.logging import logger
from app.services.llm.providers import OllamaClient, GeminiClient
from app.services.embeddings import EmbeddingModel, build_faiss_index, search_index
from app.store.document_store import document_store
from app.utils.text_processing import chunk_log, get_log_stats, read_log_file

class RAGService:
    def __init__(self):
        self.embedder = EmbeddingModel.get_instance()
        self.ollama_client = OllamaClient()
        self.gemini_client = GeminiClient()

    def _get_llm(self, mode: str):
        if mode == "cloud":
            return self.gemini_client
        return self.ollama_client

    def process_and_store(self, filename: str, filepath: str) -> dict:
        logger.info(f"--- Processing Log: {filename} ---")
        content = read_log_file(filepath)
        chunks = chunk_log(content, max_chars=settings.chunk_size)
        stats = get_log_stats(content)

        logger.info(f"Extracted {stats['total_lines']} lines into {len(chunks)} chunks.")

        if not chunks:
            logger.warning(f"No chunks created for {filename}.")
            return {"filename": filename, "chunk_count": 0, "stats": stats}

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = self.embedder.encode(chunks)
        
        logger.info("Building FAISS index...")
        index = build_faiss_index(embeddings)

        document_store.save_document(filename, {
            "chunks": chunks,
            "index": index,
            "stats": stats,
            "filepath": filepath,
        })

        logger.info(f"DONE: Processing complete for {filename}.")
        return {
            "filename": filename,
            "chunk_count": len(chunks),
            "stats": stats,
        }

    def _stream_response(self, prompt: str, mode: str, sources: list = None) -> Generator[str, None, None]:
        llm = self._get_llm(mode)
        
        if sources:
            logger.info(f"Streaming context ({len(sources)} sources) to client...")
            yield f"data: {json.dumps({'sources': sources, 'status': 'context_loaded'})}\n\n"

        try:
            logger.info(f"Starting LLM generation (mode={mode})...")
            for token in llm.generate(prompt, stream=True):
                yield f"data: {json.dumps({'token': token, 'status': 'generating'})}\n\n"
            
            logger.info("LLM generation completed successfully.")
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"

    def query_stream(self, filename: str, question: str, mode: str = None, k: int = None) -> Generator[str, None, None]:
        mode = mode or settings.default_ai_mode
        k = k or settings.top_k
        
        doc = document_store.get_document(filename)
        if not doc:
            yield f"data: {json.dumps({'error': 'File not found'})}\n\n"
            return

        query_embedding = self.embedder.encode([question])
        actual_k = min(k, len(doc["chunks"]))
        distances, indices = search_index(doc["index"], query_embedding[0], k=actual_k)

        relevant_chunks = []
        for i, idx in enumerate(indices):
            if idx < len(doc["chunks"]):
                relevant_chunks.append({
                    "text": doc["chunks"][idx],
                    "distance": float(distances[i]),
                    "index": int(idx),
                })

        context = "\n---\n".join([rc["text"] for rc in relevant_chunks])

        prompt = (
            f"Based on the following log excerpts, answer the user's question.\n\n"
            f"LOG CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {question}\n\n"
            f"Provide a detailed, technical answer."
        )

        yield from self._stream_response(prompt, mode, sources=relevant_chunks)

    def summarize_stream(self, filename: str, mode: str = None) -> Generator[str, None, None]:
        mode = mode or settings.default_ai_mode
        
        doc = document_store.get_document(filename)
        if not doc:
            yield f"data: {json.dumps({'error': 'File not found'})}\n\n"
            return

        sample_chunks = doc["chunks"][:3] + doc["chunks"][-3:]
        context = "\n---\n".join(sample_chunks)
        stats = doc["stats"]
        stats_str = f"Lines: {stats['total_lines']}, Errors: {stats['error']}, Warnings: {stats['warning']}"

        prompt = (
            f"Summarize this system log. Stats: {stats_str}\n\n"
            f"LOG EXCERPTS:\n{context}"
        )
        yield from self._stream_response(prompt, mode)

    def compare_stream(self, filename1: str, filename2: str, mode: str = None) -> Generator[str, None, None]:
        mode = mode or settings.default_ai_mode
        
        doc1 = document_store.get_document(filename1)
        doc2 = document_store.get_document(filename2)
        
        if not doc1 or not doc2:
            yield f"data: {json.dumps({'error': 'One or both files not found'})}\n\n"
            return

        prompt = (
            f"Compare {filename1} and {filename2}.\n\n"
            f"FILE 1 Stats: {doc1['stats']}\n"
            f"FILE 2 Stats: {doc2['stats']}\n"
        )
        yield from self._stream_response(prompt, mode)

rag_service = RAGService()
