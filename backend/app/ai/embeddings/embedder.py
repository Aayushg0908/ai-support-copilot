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
"""
Text embedding generator.
"""

from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2))
    
    def find_most_similar(self, query_embedding, candidate_embeddings, top_k=5):
        query_vec = np.array(query_embedding)
        candidate_matrix = np.array(candidate_embeddings)
        similarities = np.dot(candidate_matrix, query_vec)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]
        return results


embedder = Embedder()