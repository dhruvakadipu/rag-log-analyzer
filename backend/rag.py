import os
import json
import logging
import time
import requests
from google import genai
import config
from embedding import EmbeddingModel, build_faiss_index, search_index
from utils import chunk_log, get_log_stats, read_log_file

logger = logging.getLogger("log-copilot.rag")


# ---------------------------------------------------------------------------
# Ollama client — communicates with the local Ollama API
# ---------------------------------------------------------------------------


class OllamaClient:
    """Client for the local Ollama REST API."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_MODEL

    def generate(self, prompt: str, system_prompt: str = None, stream: bool = False) -> str:
        """Send a prompt to Ollama and return the generated text (or a generator)."""
        system_prompt = system_prompt or config.SYSTEM_PROMPT
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": stream,
        }

        try:
            if stream:
                return self._generate_stream(url, payload)
            
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except requests.ConnectionError:
            return (
                "❌ Could not connect to Ollama. "
                "Please make sure Ollama is running (`ollama serve`) "
                f"and accessible at {self.base_url}"
            )
        except requests.Timeout:
            return "⏱️ Ollama request timed out. The model may be loading — please try again."
        except Exception as e:
            return f"❌ Ollama error: {str(e)}"

    def _generate_stream(self, url, payload):
        """Generator for Ollama streaming response."""
        try:
            with requests.post(url, json=payload, timeout=120, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
        except Exception as e:
            yield f"\n[Error streaming from Ollama: {str(e)}]"

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            available = [m.get("name", "") for m in models]
            # Check if the model (or a variant of it) is available
            return any(self.model in name for name in available)
        except Exception:
            return False


class GeminiClient:
    """Client for Google Gemini API (using new google-genai SDK)."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.last_request_time = 0
        self.cooldown = config.GEMINI_COOLDOWN
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str = None, stream: bool = False) -> str:
        if not self.client:
            return "❌ GEMINI_API_KEY is not set or client failed to initialize."
        
        system_prompt = system_prompt or config.SYSTEM_PROMPT
        
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.cooldown:
            time.sleep(self.cooldown - elapsed)
        
        self.last_request_time = time.time()

        # Config for system prompt in new SDK
        config = {"system_instruction": system_prompt}

        try:
            if stream:
                return self._generate_stream(prompt, config)
            
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=config_sdk
            )
            return response.text
        except Exception as e:
            return f"❌ Gemini (GenAI) error: {str(e)}"

    def _generate_stream(self, prompt, config_sdk):
        """Generator for Gemini streaming response using new SDK."""
        try:
            for chunk in self.client.models.generate_content_stream(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=config_sdk
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\n[Error streaming from Gemini (GenAI): {str(e)}]"



# ---------------------------------------------------------------------------
# RAG Store — in-memory document store with FAISS indices
# ---------------------------------------------------------------------------

class RAGStore:
    """
    In-memory store for processed log files.
    Each file gets its own set of chunks and FAISS index.
    """

    def __init__(self):
        self.documents: dict = {}  # filename -> {chunks, index}
        self.embedder = EmbeddingModel.get_instance()
        self.ollama_client = OllamaClient()
        self.gemini_client = GeminiClient()

    def _get_llm(self, mode: str):
        if mode == "cloud":
            return self.gemini_client
        return self.ollama_client

    def process_and_store(self, filename: str, filepath: str) -> dict:
        """
        Read a log file, chunk it, embed the chunks, and store in FAISS.
        Returns metadata about the processed file.
        """
        logger.info(f"--- Processing Log: {filename} ---")
        content = read_log_file(filepath)
        chunks = chunk_log(content, max_chars=config.CHUNK_SIZE)
        stats = get_log_stats(content)

        logger.info(f"Extracted {stats['total_lines']} lines into {len(chunks)} chunks.")

        if not chunks:
            logger.warning(f"No chunks created for {filename}.")
            return {"filename": filename, "chunk_count": 0, "stats": stats}

        # Generate embeddings and build index
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = self.embedder.encode(chunks)
        
        logger.info("Building FAISS index...")
        index = build_faiss_index(embeddings)

        self.documents[filename] = {
            "chunks": chunks,
            "index": index,
            "stats": stats,
            "filepath": filepath,
        }

        logger.info(f"✓ Processing complete for {filename}.")
        return {
            "filename": filename,
            "chunk_count": len(chunks),
            "stats": stats,
        }

    def _stream_response(self, prompt: str, mode: str, sources: list = None):
        """Helper to stream LLM response as JSON SSE events."""
        llm = self._get_llm(mode)
        
        # Send sources first if they exist
        if sources:
            yield f"data: {json.dumps({'sources': sources, 'status': 'context_loaded'})}\n\n"

        try:
            for token in llm.generate(prompt, stream=True):
                yield f"data: {json.dumps({'token': token, 'status': 'generating'})}\n\n"
            
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'status': 'error'})}\n\n"

    def query_stream(self, filename: str, question: str, mode: str = None, k: int = None):
        mode = mode or config.DEFAULT_AI_MODE
        k = k or config.TOP_K
        if filename not in self.documents:
            yield f"data: {json.dumps({'error': 'File not found'})}\n\n"
            return

        doc = self.documents[filename]
        # Embed the question
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

        return self._stream_response(prompt, mode, sources=relevant_chunks)

    def summarize_stream(self, filename: str, mode: str = None):
        mode = mode or config.DEFAULT_AI_MODE
        if filename not in self.documents:
            yield f"data: {json.dumps({'error': 'File not found'})}\n\n"
            return

        doc = self.documents[filename]
        sample_chunks = doc["chunks"][:3] + doc["chunks"][-3:]
        context = "\n---\n".join(sample_chunks)
        stats = doc["stats"]
        stats_str = f"Lines: {stats['total_lines']}, Errors: {stats['error']}, Warnings: {stats['warning']}"

        prompt = (
            f"Summarize this system log. Stats: {stats_str}\n\n"
            f"LOG EXCERPTS:\n{context}"
        )
        return self._stream_response(prompt, mode)

    def compare_stream(self, filename1: str, filename2: str, mode: str = None):
        mode = mode or config.DEFAULT_AI_MODE
        if filename1 not in self.documents or filename2 not in self.documents:
            yield f"data: {json.dumps({'error': 'One or both files not found'})}\n\n"
            return

        doc1, doc2 = self.documents[filename1], self.documents[filename2]
        prompt = (
            f"Compare {filename1} and {filename2}.\n\n"
            f"FILE 1 Stats: {doc1['stats']}\n"
            f"FILE 2 Stats: {doc2['stats']}\n"
        )
        return self._stream_response(prompt, mode)

    def get_files(self) -> list[dict]:
        """Return list of all processed files with their stats."""
        return [
            {"filename": fname, "stats": doc["stats"], "chunk_count": len(doc["chunks"])}
            for fname, doc in self.documents.items()
        ]


# Singleton instance
rag_store = RAGStore()
