import time
from typing import Any

from label_studio_ml.model import LabelStudioMLBase

from .spacy_ner_model import SpacyNERModel
from .webapi_client import WebAPIClient
from .llm_client import LLMClient
from .logger import get_predict_logger, get_fit_logger, get_app_logger

predict_logger = get_predict_logger()
fit_logger = get_fit_logger()
app_logger = get_app_logger()

LABEL_STUDIO_LABEL_TYPE = "labels"


def _merge_two_entities(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge two entity lists, preferring primary results on overlap."""
    if not primary:
        return secondary
    if not secondary:
        return primary

    merged = list(primary)
    primary_spans = {(e["start"], e["end"]) for e in primary}

    for ent in secondary:
        span = (ent["start"], ent["end"])
        if span not in primary_spans:
            overlaps = any(
                not (ent["end"] <= p["start"] or ent["start"] >= p["end"])
                for p in primary
            )
            if not overlaps:
                merged.append(ent)

    return sorted(merged, key=lambda e: e["start"])


def _merge_entities(
    spacy_entities: list[dict[str, Any]],
    webapi_entities: list[dict[str, Any]],
    llm_entities: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Merge entities from multiple sources.
    Priority: LLM > WebAPI > spaCy
    """
    if llm_entities is None:
        llm_entities = []

    merged = _merge_two_entities(webapi_entities, spacy_entities)
    merged = _merge_two_entities(llm_entities, merged)

    return merged


def _entities_to_label_studio_result(
    entities: list[dict[str, Any]],
    from_name: str,
    to_name: str,
) -> list[dict[str, Any]]:
    results = []
    for ent in entities:
        text_len = ent["end"] - ent["start"]
        result_item = {
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
        }
        
        # Add metadata for confidence and reasoning
        metadata = {}
        if "reasoning" in ent:
            metadata["reasoning"] = ent["reasoning"]
        if "source" in ent:
            metadata["source"] = ent["source"]
        
        if metadata:
            result_item["meta"] = metadata
            
        results.append(result_item)
    return results


class CombinedNERBackend(LabelStudioMLBase):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        app_logger.info("Initializing CombinedNERBackend")
        self.spacy_model = SpacyNERModel()
        self.webapi_client = WebAPIClient()
        self.llm_client = LLMClient()
        app_logger.info(
            "Backend initialized. WebAPI configured: %s, LLM configured: %s",
            self.webapi_client.is_configured(),
            self.llm_client.is_configured(),
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
                    predict_logger.error("WebAPI call failed: %s", exc)

            llm_entities = []
            if self.llm_client.is_configured():
                try:
                    llm_entities = self.llm_client.predict_entities_sync(text)
                    predict_logger.debug("LLM found %d entities", len(llm_entities))
                except Exception as exc:
                    predict_logger.error("LLM call failed: %s", exc)

            merged = _merge_entities(spacy_entities, webapi_entities, llm_entities)
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

    def get_suggestions(self, text: str, partial: str = "", context: str = "") -> list[dict[str, Any]]:
        """
        Get entity suggestions for autocomplete functionality.
        Uses LLM if configured, falls back to spaCy predictions.
        """
        predict_logger.info("Getting suggestions for partial text: %s", partial[:50])

        if self.llm_client.is_configured():
            try:
                suggestions = self.llm_client.get_suggestions(partial, context)
                if suggestions:
                    return suggestions
            except Exception as exc:
                predict_logger.error("LLM suggestions failed: %s", exc)

        spacy_entities = self.spacy_model.predict([text])[0]
        suggestions = [
            {"text": ent["text"], "label": ent["label"], "confidence": ent.get("score", 0.8)}
            for ent in spacy_entities
            if partial.lower() in ent["text"].lower()
        ]
        return suggestions

    def normalize_entity(self, text: str, label: str) -> dict[str, Any]:
        """
        Normalize/verify an entity using LLM if available.
        """
        if self.llm_client.is_configured():
            try:
                return self.llm_client.normalize_entity_sync(text, label)
            except Exception as exc:
                predict_logger.error("LLM normalization failed: %s", exc)

        return {"text": text, "label": label, "normalized_text": text, "confidence": 1.0}

    def interactive_annotate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Interactive annotation mode for real-time predictions during editing.
        Called by Label Studio when user is actively annotating.
        
        Args:
            data: Dictionary containing task data with 'text' and optional context
            
        Returns:
            Dictionary with predictions and suggestions
        """
        predict_logger.info("Interactive annotate called")
        start_time = time.time()

        text = data.get("text", "")
        context = data.get("context", "")
        
        if not text:
            return {"result": [], "suggestions": []}

        from_name, to_name, value_key = self._get_label_config_params()

        # Get entities from all sources
        spacy_entities = self.spacy_model.predict([text])[0]
        predict_logger.debug("Interactive: spaCy found %d entities", len(spacy_entities))

        webapi_entities = []
        if self.webapi_client.is_configured():
            try:
                webapi_entities = self.webapi_client.search_entities(text)
                predict_logger.debug("Interactive: WebAPI found %d entities", len(webapi_entities))
            except Exception as exc:
                predict_logger.error("Interactive WebAPI call failed: %s", exc)

        llm_entities = []
        if self.llm_client.is_configured():
            try:
                llm_entities = self.llm_client.predict_entities_sync(text)
                predict_logger.debug("Interactive: LLM found %d entities", len(llm_entities))
            except Exception as exc:
                predict_logger.error("Interactive LLM call failed: %s", exc)

        merged = _merge_entities(spacy_entities, webapi_entities, llm_entities)
        result = _entities_to_label_studio_result(merged, from_name, to_name)

        # Generate suggestions based on partial text if context provided
        suggestions = []
        if context:
            suggestions = self.get_suggestions(text, context, text)

        elapsed = time.time() - start_time
        predict_logger.info(
            "Interactive annotate completed in %.3fs, found %d entities",
            elapsed, len(merged)
        )

        return {
            "result": result,
            "suggestions": suggestions,
            "score": sum(e.get("score", 1.0) for e in merged) / len(merged) if merged else 0.0,
        }

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
