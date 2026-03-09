import os
import time
from pathlib import Path
from typing import Any

import spacy

from .base_model import BaseNERModel
from .logger import get_predict_logger, get_fit_logger, get_training_logger
from .model_trainer import train_spacy_model, parse_label_studio_annotations

predict_logger = get_predict_logger()
fit_logger = get_fit_logger()
training_logger = get_training_logger()

DEFAULT_MODEL_NAME = os.environ.get("SPACY_MODEL", "ru_core_news_sm")
MODELS_DIR = Path(os.environ.get("MODELS_DIR", Path(__file__).parent.parent / "models"))
FINE_TUNED_MODEL_PATH = MODELS_DIR / "fine_tuned" / "model_final"


class SpacyNERModel(BaseNERModel):
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self.nlp: spacy.Language | None = None
        self._load_model()

    def _load_model(self) -> None:
        if FINE_TUNED_MODEL_PATH.exists():
            training_logger.info("Loading fine-tuned model from %s", FINE_TUNED_MODEL_PATH)
            try:
                self.nlp = spacy.load(str(FINE_TUNED_MODEL_PATH))
                training_logger.info("Fine-tuned model loaded successfully")
                return
            except Exception as exc:
                training_logger.error("Failed to load fine-tuned model: %s, falling back to base", exc)

        training_logger.info("Loading base spaCy model: %s", self.model_name)
        try:
            self.nlp = spacy.load(self.model_name)
            training_logger.info("Base model %s loaded successfully", self.model_name)
        except OSError as exc:
            training_logger.error("Failed to load model %s: %s", self.model_name, exc)
            raise

    def predict(self, texts: list[str]) -> list[list[dict[str, Any]]]:
        if not self.nlp:
            raise RuntimeError("Model not loaded")

        results = []
        start_time = time.time()
        predict_logger.info("Predict called for %d texts", len(texts))

        for text in texts:
            doc = self.nlp(text)
            entities = [
                {
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "label": ent.label_,
                    "text": ent.text,
                    "score": 1.0,
                }
                for ent in doc.ents
            ]
            results.append(entities)
            predict_logger.debug(
                "Text (len=%d) -> %d entities: %s",
                len(text),
                len(entities),
                [(e["text"], e["label"]) for e in entities],
            )

        elapsed = time.time() - start_time
        predict_logger.info("Predict completed in %.3fs for %d texts", elapsed, len(texts))
        return results

    def fit(self, annotations: list[dict[str, Any]]) -> dict[str, Any]:
        fit_logger.info("Fit called with %d annotations", len(annotations))

        if not self.nlp:
            raise RuntimeError("Model not loaded")

        output_dir = MODELS_DIR / "fine_tuned"
        start_time = time.time()

        try:
            metrics = train_spacy_model(
                nlp=self.nlp,
                training_data=annotations,
                output_dir=output_dir,
                n_iter=int(os.environ.get("TRAINING_ITERATIONS", "30")),
                drop=float(os.environ.get("TRAINING_DROPOUT", "0.3")),
            )
        except Exception as exc:
            fit_logger.error("Training failed: %s", exc, exc_info=True)
            return {"error": str(exc), "status": "failed"}

        elapsed = time.time() - start_time
        fit_logger.info(
            "Fit completed in %.1fs - status=%s, best_loss=%.4f",
            elapsed,
            metrics.get("status"),
            metrics.get("best_loss", float("inf")),
        )

        final_path = output_dir / "model_final"
        if final_path.exists():
            try:
                self.nlp = spacy.load(str(final_path))
                fit_logger.info("Reloaded fine-tuned model from %s", final_path)
            except Exception as exc:
                fit_logger.error("Failed to reload fine-tuned model: %s", exc)

        return metrics

    def fit_from_label_studio(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        fit_logger.info("Parsing Label Studio annotations from %d tasks", len(tasks))
        training_data = parse_label_studio_annotations(tasks)
        fit_logger.info("Parsed %d valid training examples", len(training_data))

        if not training_data:
            return {"error": "No valid training examples parsed", "status": "failed"}

        return self.fit(training_data)

    def load(self, model_path: str) -> None:
        training_logger.info("Loading model from: %s", model_path)
        self.nlp = spacy.load(model_path)
        training_logger.info("Model loaded from %s", model_path)

    def save(self, model_path: str) -> None:
        if not self.nlp:
            raise RuntimeError("No model to save")
        training_logger.info("Saving model to: %s", model_path)
        Path(model_path).mkdir(parents=True, exist_ok=True)
        self.nlp.to_disk(model_path)
        training_logger.info("Model saved to %s", model_path)
