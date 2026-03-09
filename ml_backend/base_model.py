from abc import ABC, abstractmethod
from typing import Any


class BaseNERModel(ABC):
    @abstractmethod
    def predict(self, texts: list[str]) -> list[list[dict[str, Any]]]:
        """
        Predict named entities for a list of texts.
        Returns list of entity lists, each entity is a dict with keys:
            start, end, label, text
        """

    @abstractmethod
    def fit(self, annotations: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Fine-tune the model on annotated examples.
        annotations: list of dicts with keys: text, entities (list of (start, end, label))
        Returns training metrics dict.
        """

    @abstractmethod
    def load(self, model_path: str) -> None:
        """Load model from path."""

    @abstractmethod
    def save(self, model_path: str) -> None:
        """Save model to path."""
