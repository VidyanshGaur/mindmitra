"""Small, explainable intent-classification pipeline for MindMitra."""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


DATASET_PATH = Path(__file__).parent / "data" / "intents.csv"


def train_intent_model() -> Pipeline:
    """Train a TF-IDF + Logistic Regression intent classifier from local CSV data."""
    dataset = pd.read_csv(DATASET_PATH)
    required_columns = {"text", "intent"}
    if not required_columns.issubset(dataset.columns):
        raise ValueError("data/intents.csv must contain text and intent columns.")

    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), stop_words="english")),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    ).fit(dataset["text"], dataset["intent"])


def predict_intent(model: Pipeline, text: str) -> tuple[str, float]:
    """Return the predicted intent and its probability percentage."""
    intent = str(model.predict([text])[0])
    confidence = float(model.predict_proba([text]).max() * 100)
    return intent, confidence
