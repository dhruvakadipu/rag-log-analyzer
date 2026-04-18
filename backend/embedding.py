"""
Cloud embedding model using Google Gemini API and FAISS index management.
"""

import os
import numpy as np
import faiss
import google.generativeai as genai

class EmbeddingModel:
    """
    Singleton-style embedding model that uses Google's text-embedding-004.
    This saves memory by moving the embedding process to the cloud.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            print("[warning] GEMINI_API_KEY not found. Embeddings will fail in Cloud mode.")

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode a list of texts into embeddings using Gemini API.
        Returns numpy float32 array.
        """
        if not self.api_key:
            # Fallback for local testing if no key provided, though it'll likely error later
            return np.zeros((len(texts), self.dimension), dtype=np.float32)

        try:
            # Using text-embedding-004 (768 dimensions)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=texts,
                task_type="retrieval_document"
            )
            return np.array(result['embedding'], dtype=np.float32)
        except Exception as e:
            print(f"[embedding] Error during cloud encoding: {str(e)}")
            # Return zeros as a safe fallback to prevent crash, though RAG will ignore it
            return np.zeros((len(texts), self.dimension), dtype=np.float32)

    @property
    def dimension(self) -> int:
        return 768  # Gemini text-embedding-004 dimension


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    """Create a FAISS L2 index from a numpy array of embeddings."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index


def search_index(index: faiss.IndexFlatL2, query_embedding: np.ndarray, k: int = 5) -> tuple:
    """
    Search the FAISS index for top-k nearest neighbors.
    """
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)
    
    # Ensure query embedding is the right dimension
    if query_embedding.shape[1] != index.d:
        # This might happen if switching models mid-session
        return np.array([], dtype=np.float32), np.array([], dtype=np.int64)

    distances, indices = index.search(query_embedding, k)
    return distances[0], indices[0]
