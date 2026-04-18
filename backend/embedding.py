import os
import numpy as np
import faiss
from google import genai
import config

class EmbeddingModel:
    """
    Hybrid embedding model. 
    Uses Gemini Cloud by default if API key is present.
    Falls back to Local Sentence-Transformers if offline or no key.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.local_model = None
        self.client = None
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            print("[embedding] Gemini Cloud (google-genai) enabled.")
        else:
            print("[embedding] GEMINI_API_KEY not found. Fallback to Local mode.")

    def _get_local_model(self):
        """Lazy load the local model only when actually needed to save RAM."""
        if os.getenv("RENDER") or os.getenv("PORT"):
            # Simple check for cloud environment to prevent RAM-based crashes
            raise Exception("Local embedding model is disabled in Cloud environment to prevent memory issues. Please ensure GEMINI_API_KEY is valid.")
            
        if self.local_model is None:
            from sentence_transformers import SentenceTransformer
            print(f"[embedding] Loading local Sentence-Transformer ({config.LOCAL_EMBEDDING_MODEL})...")
            self.local_model = SentenceTransformer(config.LOCAL_EMBEDDING_MODEL)
        return self.local_model

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode texts using Cloud by default, with Local fallback.
        """
        # Try Cloud first if Key is present
        if self.client:
            try:
                # New SDK: contents is used for multiple inputs
                result = self.client.models.embed_content(
                    model=config.GEMINI_EMBEDDING_MODEL,
                    contents=texts
                )
                
                # result.embeddings is a list of Embedding objects
                embeddings = [e.values for e in result.embeddings]
                return np.array(embeddings, dtype=np.float32)
            except Exception as e:
                print(f"[embedding] Cloud failed: {e}. Attempting local fallback...")

        # Local Fallback
        model = self._get_local_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return np.array(embeddings, dtype=np.float32)

    @property
    def dimension(self) -> int:
        # We handle dynamic dimensions in the FAISS index builder
        # but Gemini is typically 768 and MiniLM is 384.
        if self.api_key:
            return 768
        return 384


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    """Create a FAISS L2 index from a numpy array of embeddings."""
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index


def search_index(index: faiss.IndexFlatL2, query_embedding: np.ndarray, k: int = None) -> tuple:
    """Search the FAISS index for top-k nearest neighbors."""
    k = k or config.TOP_K
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)
    
    # Check for dimension mismatch (e.g., if you switch modes mid-session)
    if query_embedding.shape[1] != index.d:
        print(f"[embedding] Dimension mismatch: query({query_embedding.shape[1]}) vs index({index.d})")
        return np.array([], dtype=np.float32), np.array([], dtype=np.int64)

    distances, indices = index.search(query_embedding, k)
    return distances[0], indices[0]
