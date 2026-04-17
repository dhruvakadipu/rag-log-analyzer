"""
RAG (Retrieval-Augmented Generation) pipeline using FAISS + Ollama.
"""

import os
import json
import requests
import google.generativeai as genai
from embedding import EmbeddingModel, build_faiss_index, search_index
from utils import chunk_log, get_log_stats, read_log_file


# ---------------------------------------------------------------------------
# Ollama client — communicates with the local Ollama API
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b")

SYSTEM_PROMPT = (
    "You are a highly skilled systems debugging assistant. "
    "Analyze logs carefully and provide precise, technical, and actionable insights. "
    "Focus on identifying root causes, anomalies, and performance issues. "
    "Avoid generic responses."
)


class OllamaClient:
    """Client for the local Ollama REST API."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL

    def generate(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        """Send a prompt to Ollama and return the generated text."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }

        try:
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
    """Client for Google Gemini API."""
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        if not self.api_key:
            return "❌ GEMINI_API_KEY is not set. Please add it to your .env file to use Cloud mode."
        try:
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ Gemini error: {str(e)}"



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
        content = read_log_file(filepath)
        chunks = chunk_log(content, max_chars=200)
        stats = get_log_stats(content)

        if not chunks:
            return {"filename": filename, "chunk_count": 0, "stats": stats}

        # Generate embeddings and build index
        embeddings = self.embedder.encode(chunks)
        index = build_faiss_index(embeddings)

        self.documents[filename] = {
            "chunks": chunks,
            "index": index,
            "stats": stats,
            "filepath": filepath,
        }

        return {
            "filename": filename,
            "chunk_count": len(chunks),
            "stats": stats,
        }

    def query(self, filename: str, question: str, mode: str = "local", k: int = 5) -> dict:
        """
        RAG query: embed the question, retrieve top-k chunks, generate answer.
        """
        if filename not in self.documents:
            return {
                "answer": f"File '{filename}' has not been processed yet. Please upload it first.",
                "sources": [],
            }

        doc = self.documents[filename]
        chunks = doc["chunks"]
        index = doc["index"]

        # Embed the question
        query_embedding = self.embedder.encode([question])

        # Retrieve top-k relevant chunks
        actual_k = min(k, len(chunks))
        distances, indices = search_index(index, query_embedding[0], k=actual_k)

        # Gather relevant chunks
        relevant_chunks = []
        for i, idx in enumerate(indices):
            if idx < len(chunks):
                relevant_chunks.append({
                    "text": chunks[idx],
                    "distance": float(distances[i]),
                    "index": int(idx),
                })

        # Build the prompt with context
        context = "\n---\n".join([rc["text"] for rc in relevant_chunks])
        prompt = (
            f"Based on the following log excerpts, answer the user's question.\n\n"
            f"LOG CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {question}\n\n"
            f"Provide a detailed, technical answer. Reference specific log entries when possible."
        )

        llm = self._get_llm(mode)
        answer = llm.generate(prompt)

        return {
            "answer": answer,
            "sources": relevant_chunks,
        }

    def summarize(self, filename: str, mode: str = "local") -> dict:
        """Generate a high-level summary of the log file."""
        if filename not in self.documents:
            return {"summary": f"File '{filename}' has not been processed yet."}

        doc = self.documents[filename]
        chunks = doc["chunks"]
        stats = doc["stats"]

        # Use a representative sample of chunks (first, middle, last + error chunks)
        sample_chunks = []
        if len(chunks) <= 10:
            sample_chunks = chunks
        else:
            # First 3, last 3, and up to 4 with errors/warnings
            sample_chunks = chunks[:3] + chunks[-3:]
            for c in chunks:
                if any(kw in c.upper() for kw in ["ERROR", "WARNING"]):
                    if c not in sample_chunks:
                        sample_chunks.append(c)
                    if len(sample_chunks) >= 12:
                        break

        context = "\n---\n".join(sample_chunks)
        stats_str = (
            f"Total lines: {stats['total_lines']}, "
            f"Errors: {stats['error']}, "
            f"Warnings: {stats['warning']}, "
            f"Info: {stats['info']}"
        )

        prompt = (
            f"Summarize the following system log. Provide:\n"
            f"1. A brief overview of what the system was doing\n"
            f"2. Key issues and errors found\n"
            f"3. Recommendations for the engineering team\n\n"
            f"LOG STATISTICS: {stats_str}\n\n"
            f"LOG EXCERPTS:\n{context}"
        )

        llm = self._get_llm(mode)
        summary = llm.generate(prompt)
        return {"summary": summary, "stats": stats}

    def compare(self, filename1: str, filename2: str, mode: str = "local") -> dict:
        """Compare two log files and highlight differences."""
        if filename1 not in self.documents:
            return {"comparison": f"File '{filename1}' has not been processed yet."}
        if filename2 not in self.documents:
            return {"comparison": f"File '{filename2}' has not been processed yet."}

        doc1 = self.documents[filename1]
        doc2 = self.documents[filename2]

        stats1 = doc1["stats"]
        stats2 = doc2["stats"]

        # Sample chunks from each file
        sample1 = doc1["chunks"][:5]
        sample2 = doc2["chunks"][:5]

        # Include error/warning chunks
        for c in doc1["chunks"]:
            if any(kw in c.upper() for kw in ["ERROR", "WARNING"]) and c not in sample1:
                sample1.append(c)
                if len(sample1) >= 8:
                    break

        for c in doc2["chunks"]:
            if any(kw in c.upper() for kw in ["ERROR", "WARNING"]) and c not in sample2:
                sample2.append(c)
                if len(sample2) >= 8:
                    break

        prompt = (
            f"Compare these two log files and identify differences:\n\n"
            f"=== FILE 1: {filename1} ===\n"
            f"Stats: Lines={stats1['total_lines']}, Errors={stats1['error']}, "
            f"Warnings={stats1['warning']}\n"
            f"Sample entries:\n" + "\n".join(sample1) + "\n\n"
            f"=== FILE 2: {filename2} ===\n"
            f"Stats: Lines={stats2['total_lines']}, Errors={stats2['error']}, "
            f"Warnings={stats2['warning']}\n"
            f"Sample entries:\n" + "\n".join(sample2) + "\n\n"
            f"Provide:\n"
            f"1. Key differences between the two logs\n"
            f"2. Which log indicates more severe issues\n"
            f"3. Common patterns and divergences"
        )

        llm = self._get_llm(mode)
        comparison = llm.generate(prompt)
        return {
            "comparison": comparison,
            "stats1": stats1,
            "stats2": stats2,
        }

    def get_files(self) -> list[dict]:
        """Return list of all processed files with their stats."""
        return [
            {"filename": fname, "stats": doc["stats"], "chunk_count": len(doc["chunks"])}
            for fname, doc in self.documents.items()
        ]


# Singleton instance
rag_store = RAGStore()
