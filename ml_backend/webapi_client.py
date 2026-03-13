import os
import time
from typing import Any

import requests

from .logger import get_webapi_logger

logger = get_webapi_logger()

WEBAPI_BASE_URL = os.environ.get("WEBAPI_BASE_URL", "")
WEBAPI_TOKEN = os.environ.get("WEBAPI_TOKEN", "")
WEBAPI_TIMEOUT = int(os.environ.get("WEBAPI_TIMEOUT", "10"))
WEBAPI_MAX_RETRIES = int(os.environ.get("WEBAPI_MAX_RETRIES", "3"))
WEBAPI_RETRY_DELAY = float(os.environ.get("WEBAPI_RETRY_DELAY", "1.0"))


class WebAPIClient:
    def __init__(
        self,
        base_url: str = WEBAPI_BASE_URL,
        token: str = WEBAPI_TOKEN,
        timeout: int = WEBAPI_TIMEOUT,
        max_retries: int = WEBAPI_MAX_RETRIES,
        retry_delay: float = WEBAPI_RETRY_DELAY,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.session.headers.update({"Content-Type": "application/json; charset=utf-8"})

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def search_entities(self, text: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            logger.debug("WebAPI not configured, skipping entity search")
            return []

        url = f"{self.base_url}/entities/search"
        payload = {"text": text}
        logger.info("Calling WebAPI entity search: url=%s, text_len=%d", url, len(text))

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                entities = data.get("entities", [])
                
                # Add source and default reasoning if not present
                for ent in entities:
                    ent["source"] = "webapi"
                    if "reasoning" not in ent:
                        ent["reasoning"] = f"Получено из внешнего API: {ent.get('label', 'UNKNOWN')}"
                    if "score" not in ent:
                        ent["score"] = 0.85
                
                logger.info("WebAPI returned %d entities for text_len=%d", len(entities), len(text))
                return entities
            except requests.exceptions.Timeout:
                logger.error(
                    "WebAPI timeout on attempt %d/%d: url=%s", attempt, self.max_retries, url
                )
            except requests.exceptions.ConnectionError as exc:
                logger.error(
                    "WebAPI connection error on attempt %d/%d: %s", attempt, self.max_retries, exc
                )
            except requests.exceptions.HTTPError as exc:
                logger.error("WebAPI HTTP error: %s", exc)
                break
            except Exception as exc:
                logger.error("WebAPI unexpected error on attempt %d/%d: %s", attempt, self.max_retries, exc)

            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)

        logger.error("WebAPI failed after %d attempts, returning empty list", self.max_retries)
        return []

    def normalize_entity(self, text: str, label: str) -> dict[str, Any]:
        if not self.is_configured():
            return {"text": text, "label": label}

        url = f"{self.base_url}/entities/normalize"
        payload = {"text": text, "label": label}
        logger.info("Calling WebAPI normalize: text=%s, label=%s", text[:50], label)

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("WebAPI normalize failed: %s", exc)
            return {"text": text, "label": label}
