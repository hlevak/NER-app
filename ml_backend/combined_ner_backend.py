import time
from typing import Any

from label_studio_ml.model import LabelStudioMLBase

from .spacy_ner_model import SpacyNERModel
from .webapi_client import WebAPIClient
from .logger import get_predict_logger, get_fit_logger, get_app_logger

predict_logger = get_predict_logger()
fit_logger = get_fit_logger()
app_logger = get_app_logger()

LABEL_STUDIO_LABEL_TYPE = "labels"


def _merge_entities(
    spacy_entities: list[dict[str, Any]],
    webapi_entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge spaCy and WebAPI entities, preferring WebAPI results on overlap."""
    if not webapi_entities:
        return spacy_entities

    merged = list(webapi_entities)
    webapi_spans = {(e["start"], e["end"]) for e in webapi_entities}

    for ent in spacy_entities:
        span = (ent["start"], ent["end"])
        if span not in webapi_spans:
            overlaps = any(
                not (ent["end"] <= w["start"] or ent["start"] >= w["end"])
                for w in webapi_entities
            )
            if not overlaps:
                merged.append(ent)

    return sorted(merged, key=lambda e: e["start"])


def _entities_to_label_studio_result(
    entities: list[dict[str, Any]],
    from_name: str,
    to_name: str,
) -> list[dict[str, Any]]:
    results = []
    for ent in entities:
        text_len = ent["end"] - ent["start"]
        results.append({
            "from_name": from_name,
            "to_name": to_name,
            "type": LABEL_STUDIO_LABEL_TYPE,
            "value": {
                "start": ent["start"],
                "end": ent["end"],
                "text": ent.get("text", ""),
                "labels": [ent["label"]],
            },
            "score": ent.get("score", 1.0),
        })
    return results


class CombinedNERBackend(LabelStudioMLBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        app_logger.info("Initializing CombinedNERBackend")
        self.spacy_model = SpacyNERModel()
        self.webapi_client = WebAPIClient()
        app_logger.info(
            "Backend initialized. WebAPI configured: %s", self.webapi_client.is_configured()
        )

    def predict(self, tasks: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        predict_logger.info("Predict called for %d tasks", len(tasks))
        start_time = time.time()

        from_name, to_name, value_key = self._get_label_config_params()

        predictions = []
        for task in tasks:
            text = task.get("data", {}).get(value_key, "") or task.get("data", {}).get("text", "")
            if not text:
                predictions.append({"result": [], "score": 0.0})
                continue

            spacy_entities = self.spacy_model.predict([text])[0]
            predict_logger.debug("spaCy found %d entities", len(spacy_entities))

            webapi_entities = []
            if self.webapi_client.is_configured():
                try:
                    webapi_entities = self.webapi_client.search_entities(text)
                    predict_logger.debug("WebAPI found %d entities", len(webapi_entities))
                except Exception as exc:
                    predict_logger.error("WebAPI call failed, using spaCy only: %s", exc)

            merged = _merge_entities(spacy_entities, webapi_entities)
            result = _entities_to_label_studio_result(merged, from_name, to_name)

            avg_score = (
                sum(e.get("score", 1.0) for e in merged) / len(merged) if merged else 0.0
            )
            predictions.append({"result": result, "score": avg_score})

        elapsed = time.time() - start_time
        predict_logger.info(
            "Predict completed in %.3fs for %d tasks, total entities: %d",
            elapsed,
            len(tasks),
            sum(len(p["result"]) for p in predictions),
        )
        return predictions

    def fit(self, annotations: list[dict[str, Any]], workdir: str | None = None, **kwargs: Any) -> dict[str, Any]:
        fit_logger.info("Fit called with %d annotation items", len(annotations))
        start_time = time.time()

        if not annotations:
            fit_logger.warning("No annotations provided for training")
            return {"status": "skipped", "reason": "no annotations"}

        metrics = self.spacy_model.fit_from_label_studio(annotations)
        elapsed = time.time() - start_time
        fit_logger.info("Fit finished in %.1fs: %s", elapsed, metrics.get("status"))
        return metrics

    def _get_label_config_params(self) -> tuple[str, str, str]:
        try:
            from_name, to_name, value_key = "", "text", "text"
            if self.label_config:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(self.label_config)
                labels_el = root.find(".//Labels")
                text_el = root.find(".//Text")
                if labels_el is not None:
                    from_name = labels_el.get("name", "label")
                if text_el is not None:
                    to_name = text_el.get("name", "text")
                    value_key = text_el.get("value", "$text").lstrip("$")
            return from_name or "label", to_name or "text", value_key or "text"
        except Exception as exc:
            app_logger.error("Failed to parse label config: %s", exc)
            return "label", "text", "text"
