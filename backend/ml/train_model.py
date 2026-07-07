"""
Train an ML classifier on generated ticket data.
"""

import json
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report


def load_data(filepath: str = "training_data.json"):
    """Load training data from JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    
    texts = []
    labels = []
    
    for item in data:
        # Combine title and description for training
        text = f"{item['title']} {item['description']}"
        texts.append(text)
        labels.append(item["category"])
    
    return texts, labels


def train_model(texts, labels):
    """Train the classification model."""
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )
    
    # Create pipeline
    pipeline = Pipeline([
        ("vectorizer", TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),  # Single words, pairs, and triples
            stop_words="english",
            sublinear_tf=True,  # Log scaling for term frequency
        )),
        ("classifier", LogisticRegression(
            multi_class="multinomial",
            max_iter=2000,
            C=1.0,
            class_weight="balanced",  # Handle imbalanced categories
        )),
    ])
    
    # Train
    print("Training model...")
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    print("\nCross-validation scores:")
    scores = cross_val_score(pipeline, texts, labels, cv=5)
    print(f"  Mean accuracy: {scores.mean():.3f} (+/- {scores.std() * 2:.3f})")
    
    print("\nTest set performance:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    return pipeline


def save_model(pipeline, filepath: str = "ml_classifier.pkl"):
    """Save trained model to disk."""
    with open(filepath, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"\nModel saved to: {filepath}")


if __name__ == "__main__":
    print("Loading training data...")
    texts, labels = load_data()
    print(f"Loaded {len(texts)} examples across {len(set(labels))} categories")
    
    pipeline = train_model(texts, labels)
    save_model(pipeline)