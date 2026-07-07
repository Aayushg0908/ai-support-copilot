"""
Hybrid classifier: ML model first, Gemini as fallback.
"""

import pickle
from typing import Tuple
from google import genai

from app.core.config import settings
from app.ai.classification.classifier import TicketClassifier


class HybridClassifier:
    """
    Uses ML model for speed, falls back to Gemini for accuracy.
    
    Strategy:
    1. Try ML model first (fast, free, offline)
    2. If ML confidence < 0.8, call Gemini (slower, more accurate)
    3. ML model improves over time as more tickets are labeled
    """
    
    def __init__(self, model_path: str = "ml/ml_classifier.pkl"):
        self.ml_model = None
        self.llm_classifier = TicketClassifier()
        self._load_ml_model(model_path)
    
    def _load_ml_model(self, path: str):
        """Load the trained ML model."""
        try:
            with open(path, "rb") as f:
                self.ml_model = pickle.load(f)
            print("ML model loaded successfully")
        except FileNotFoundError:
            print("No ML model found. Using Gemini only.")
    
    def classify(self, title: str, description: str) -> Tuple[str, str, float]:
        """
        Classify a ticket using hybrid approach.
        """
        text = f"{title} {description}"
        
        # Try ML model first
        if self.ml_model:
            try:
                category = self.ml_model.predict([text])[0]
                probabilities = self.ml_model.predict_proba([text])[0]
                confidence = float(max(probabilities))
                
                # If ML is confident, use it
                if confidence > 0.8:
                    # Also get priority from Gemini (ML doesn't predict priority yet)
                    priority, _ = self.llm_classifier.classify_priority_only(
                        title, description
                    )
                    return category, priority, confidence
            except Exception as e:
                print(f"ML classification failed: {e}")
        
        # Fall back to Gemini
        return self.llm_classifier.classify(title, description)