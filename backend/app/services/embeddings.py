import numpy as np
import faiss
from google import genai

from app.core.config import settings
from app.core.logging import logger

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
        self.api_key = settings.gemini_api_key
        self.local_model = None
        self.client = None
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini Cloud (google-genai) enabled.")
        else:
            logger.warning("GEMINI_API_KEY not found. Fallback to Local mode.")

    def _get_local_model(self):
        """Lazy load the local model only when actually needed to save RAM."""
        is_cloud = settings.environment == "cloud"
        
        if is_cloud:
            raise Exception("Local embedding model is disabled in Cloud environment to prevent memory issues. Please ensure GEMINI_API_KEY is valid.")
            
        if self.local_model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading local Sentence-Transformer ({settings.local_embedding_model})...")
            self.local_model = SentenceTransformer(settings.local_embedding_model)
        return self.local_model

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.client:
            try:
                result = self.client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=texts
                )
                embeddings = [e.values for e in result.embeddings]
                return np.array(embeddings, dtype=np.float32)
            except Exception as e:
                logger.error(f"Cloud embedding failed: {e}. Attempting local fallback...")

        model = self._get_local_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return np.array(embeddings, dtype=np.float32)

    @property
    def dimension(self) -> int:
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
    k = k or settings.top_k
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)
    
    if query_embedding.shape[1] != index.d:
        logger.error(f"Dimension mismatch: query({query_embedding.shape[1]}) vs index({index.d})")
        return np.array([], dtype=np.float32), np.array([], dtype=np.int64)

    distances, indices = index.search(query_embedding, k)
    return distances[0], indices[0]
