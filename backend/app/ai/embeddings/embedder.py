"""
Text embedding generator.

Converts text into numerical vectors for similarity comparison.
Uses Sentence Transformers (all-MiniLM-L6-v2) which produces
384-dimensional embeddings.

These embeddings enable:
- Finding similar tickets by comparing vectors
- Semantic search (finding by meaning, not just keywords)
- Clustering related tickets
"""

from typing import List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    """
    Handles text-to-vector conversion.
    
    The model is loaded once and reused for all requests.
    This avoids reloading the model for every API call.
    
    Model: all-MiniLM-L6-v2
    - 384 dimensions
    - 80MB size
    - Fast inference (milliseconds per text)
    - Good balance of speed and accuracy
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Lazy loading: model is loaded when first used,
        not when the class is instantiated. This allows
        importing this module without loading the model
        immediately.
        """
        self.model_name = model_name
        self._model: Optional[SentenceTransformer] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """
        Get or load the model.
        
        First call loads the model (slow), subsequent
        calls return the cached model (instant).
        """
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            print("Model loaded successfully")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Convert a single text to an embedding vector.
        
        Args:
            text: Any string (ticket title, description, etc.)
        
        Returns:
            List of 384 floating-point numbers
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Convert multiple texts to embedding vectors.
        
        Batching is faster than encoding one at a time
        because the model can process multiple texts
        in parallel on the GPU/CPU.
        
        Args:
            texts: List of strings
        
        Returns:
            List of 384-dimensional vectors
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    
    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Returns a score from -1 to 1:
        - 1.0: Texts are identical in meaning
        - 0.0: Texts are unrelated
        - -1.0: Texts are opposite (rare with embeddings)
        
        We normalize embeddings, so dot product equals
        cosine similarity.
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2))
    
    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5,
    ) -> List[tuple]:
        """
        Find the most similar embeddings to a query.
        
        Args:
            query_embedding: The embedding to compare against
            candidate_embeddings: List of embeddings to search
            top_k: Number of top matches to return
        
        Returns:
            List of (index, similarity_score) tuples, sorted by score descending
        
        Example:
            query = embedder.embed_text("login error")
            candidates = embedder.embed_texts(["password reset", "billing issue", "login failed"])
            results = embedder.find_most_similar(query, candidates, top_k=2)
            # Returns [(2, 0.95), (0, 0.62)] - "login failed" is most similar
        """
        query_vec = np.array(query_embedding)
        candidate_matrix = np.array(candidate_embeddings)
        
        # Compute all similarities at once (efficient)
        similarities = np.dot(candidate_matrix, query_vec)
        
        # Get indices of top K matches
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append((int(idx), float(similarities[idx])))
        
        return results


# Module-level singleton instance
# Every file imports this same instance
embedder = Embedder()