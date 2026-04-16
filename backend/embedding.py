"""
Local embedding model using sentence-transformers and FAISS index management.
"""

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    """
    Singleton-style embedding model that loads sentence-transformers/all-MiniLM-L6-v2.
    The model is loaded once and reused for all requests.
    """

    _instance = None
    _model = None

    @classmethod
    def get_instance(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if EmbeddingModel._model is None:
            print("[embedding] Loading sentence-transformers model: all-MiniLM-L6-v2 ...")
            EmbeddingModel._model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[embedding] Model loaded successfully.")

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode a list of texts into embeddings.
        Returns numpy float32 array of shape (n, 384).
        """
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return np.array(embeddings, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return 384


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    """Create a FAISS L2 index from a numpy array of embeddings."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index


def search_index(index: faiss.IndexFlatL2, query_embedding: np.ndarray, k: int = 5) -> tuple:
    """
    Search the FAISS index for top-k nearest neighbors.
    Returns (distances, indices) arrays.
    """
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)
    distances, indices = index.search(query_embedding, k)
    return distances[0], indices[0]
