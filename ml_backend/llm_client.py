import os
import time
import json
from typing import Any
from enum import Enum

import httpx

from .logger import get_llm_logger

logger = get_llm_logger()

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "lmstudio")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "2"))
LLM_RETRY_DELAY = float(os.environ.get("LLM_RETRY_DELAY", "1.0"))
LLM_ENABLED = os.environ.get("LLM_ENABLED", "false").lower() == "true"


class LLMProvider(Enum):
    LM_STUDIO = "lmstudio"
    LLAMA_CPP = "llamacpp"
    OPENAI_COMPATIBLE = "openai_compatible"


NER_SYSTEM_PROMPT = """Ты - эксперт в распознавании именованных сущностей (NER).
Твоя задача - найти и классифицировать сущности в тексте.

Допустимые типы сущностей:
- PER (Person) - имена людей
- ORG (Organization) - организации, компании
- LOC (Location) - географические локации, города, страны
- DATE (Date) - даты, в том числе частичные (год, месяц и год)
- ES (Электронный след) - контактные и цифровые идентификаторы: телефоны, email, аккаунты (@username) и названия групп/каналов в мессенджерах и соцсетях, сайты, IP-адреса, номера банковских карт и счетов, адреса криптокошельков. Если рядом с идентификатором есть название — включи оба в один span. Пример: {"label": "ES", "text": "Яндекс (www.ya.ru)"}. Используй ES когда идентификатор написан словами или косвенно упомянут.

Ответь строго в формате JSON:
{
  "entities": [
    {"label": "PER", "text": "Иван Иванов"},
    {"label": "ORG", "text": "Яндекс"}
  ]
}

Поле "text" должно содержать точную подстроку из исходного текста.
Если сущностей нет, верни {"entities": []}.
"""

_ALLOWED_LABELS = {"PER", "ORG", "LOC", "DATE", "ES"}

NORMALIZE_SYSTEM_PROMPT = """Ты - эксперт по нормализации именованных сущностей.
Твоя задача - привести сущность к канонической форме.

Ответь строго в формате JSON:
{
  "normalized_text": "...",
  "confidence": 0.95
}
"""

AUTOCOMPLETE_SYSTEM_PROMPT = """Ты помощник для автодополнения текста при разметке сущностей.
На основе частичного ввода предложи возможные варианты сущностей.

Ответь строго в формате JSON:
{
  "suggestions": [
    {"text": "...", "label": "PER", "confidence": 0.9}
  ]
}
"""


class LLMClient:
    def __init__(
        self,
        provider: str = LLM_PROVIDER,
        base_url: str = LLM_BASE_URL,
        model: str = LLM_MODEL,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        timeout: int = LLM_TIMEOUT,
        max_retries: int = LLM_MAX_RETRIES,
        retry_delay: float = LLM_RETRY_DELAY,
        enabled: bool = LLM_ENABLED,
    ) -> None:
        self.provider = LLMProvider(provider)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enabled = enabled
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return self.enabled and bool(self.base_url)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _build_messages(self, system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        if self.model:
            messages.append({"role": "user", "content": user_prompt})
        else:
            messages.append({"role": "user", "content": user_prompt})
        return messages

    def _build_payload(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.model:
            payload["model"] = self.model
        return payload

    async def _call_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}

        client = self._get_client()

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("LLM API call attempt %d/%d to %s", attempt, self.max_retries, url)
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                logger.error("LLM timeout on attempt %d/%d", attempt, self.max_retries)
            except httpx.ConnectError as exc:
                logger.error("LLM connection error on attempt %d/%d: %s", attempt, self.max_retries, exc)
            except httpx.HTTPStatusError as exc:
                logger.error("LLM HTTP error: %s", exc)
                raise
            except Exception as exc:
                logger.error("LLM unexpected error on attempt %d/%d: %s", attempt, self.max_retries, exc)

            if attempt < self.max_retries:
                wait_time = self.retry_delay * attempt
                logger.info("Retrying LLM call in %.1fs...", wait_time)
                time.sleep(wait_time)

        raise Exception(f"LLM API failed after {self.max_retries} attempts")

    def _parse_response(self, response: dict[str, Any]) -> str:
        try:
            choices = response.get("choices", [])
            if not choices:
                raise ValueError("No choices in response")
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content.strip()
        except Exception as exc:
            logger.error("Failed to parse LLM response: %s", exc)
            raise

    def _extract_json(self, text: str) -> dict[str, Any]:
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].strip()
            else:
                json_str = text.strip()
            return json.loads(json_str)
        except Exception as exc:
            logger.error("Failed to extract JSON from LLM response: %s", exc)
            return {}

    def _fix_offsets(self, source: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Replace LLM-reported offsets with positions found via str.find."""
        fixed = []
        search_from = 0
        for ent in sorted(entities, key=lambda e: e.get("start", 0)):
            ent_text = ent.get("text", "").strip()
            if not ent_text:
                continue
            pos = source.find(ent_text, search_from)
            if pos == -1:
                pos = source.find(ent_text)
            if pos == -1:
                logger.warning("Entity text not found in source, dropping: %r", ent_text)
                continue
            ent["start"] = pos
            ent["end"] = pos + len(ent_text)
            search_from = ent["end"]
            fixed.append(ent)
        return fixed

    async def predict_entities(self, text: str) -> list[dict[str, Any]]:
        if not self.is_configured():
            logger.debug("LLM not configured, skipping entity prediction")
            return []

        user_prompt = f"Найди все именованные сущности в тексте:\n\n{text}\n\nОтветь только в формате JSON."
        messages = self._build_messages(NER_SYSTEM_PROMPT, user_prompt)
        payload = self._build_payload(messages)

        start_time = time.time()
        try:
            response = await self._call_api(payload)
            content = self._parse_response(response)
            data = self._extract_json(content)
            entities = data.get("entities", [])

            entities = [e for e in entities if e.get("label") in _ALLOWED_LABELS]
            entities = self._fix_offsets(text, entities)

            for ent in entities:
                ent["source"] = "llm"
                ent["score"] = ent.get("score", 0.9)
                if "reasoning" not in ent:
                    ent["reasoning"] = "Определено LLM моделью"

            elapsed = time.time() - start_time
            logger.info("LLM NER completed in %.3fs, found %d entities", elapsed, len(entities))
            return entities
        except Exception as exc:
            logger.error("LLM NER failed: %s", exc)
            return []

    async def normalize_entity(self, text: str, label: str) -> dict[str, Any]:
        if not self.is_configured():
            return {"text": text, "label": label, "normalized_text": text, "confidence": 1.0}

        user_prompt = f"Нормализуй сущность:\nТекст: {text}\nТип: {label}\n\nОтветь только в формате JSON."
        messages = self._build_messages(NORMALIZE_SYSTEM_PROMPT, user_prompt)
        payload = self._build_payload(messages)

        try:
            response = await self._call_api(payload)
            content = self._parse_response(response)
            data = self._extract_json(content)

            result = {
                "text": text,
                "label": label,
                "normalized_text": data.get("normalized_text", text),
                "confidence": data.get("confidence", 0.9),
            }
            logger.info("LLM normalized entity: %s -> %s", text, result["normalized_text"])
            return result
        except Exception as exc:
            logger.error("LLM normalization failed: %s", exc)
            return {"text": text, "label": label, "normalized_text": text, "confidence": 1.0}

    async def get_suggestions(self, partial_text: str, context: str = "") -> list[dict[str, Any]]:
        if not self.is_configured():
            return []

        user_prompt = f"Предложи варианты автодополнения:\nЧастичный ввод: {partial_text}"
        if context:
            user_prompt += f"\nКонтекст: {context}"
        user_prompt += "\n\nОтветь только в формате JSON."

        messages = self._build_messages(AUTOCOMPLETE_SYSTEM_PROMPT, user_prompt)
        payload = self._build_payload(messages)

        try:
            response = await self._call_api(payload)
            content = self._parse_response(response)
            data = self._extract_json(content)
            suggestions = data.get("suggestions", [])
            logger.info("LLM generated %d suggestions for partial text", len(suggestions))
            return suggestions
        except Exception as exc:
            logger.error("LLM suggestions failed: %s", exc)
            return []

    def predict_entities_sync(self, text: str) -> list[dict[str, Any]]:
        import asyncio
        try:
            return asyncio.run(self.predict_entities(text))
        except Exception as exc:
            logger.error("LLM sync call failed: %s", exc)
            return []

    def normalize_entity_sync(self, text: str, label: str) -> dict[str, Any]:
        import asyncio
        try:
            return asyncio.run(self.normalize_entity(text, label))
        except Exception as exc:
            logger.error("LLM sync normalization failed: %s", exc)
            return {"text": text, "label": label, "normalized_text": text, "confidence": 1.0}

    def close(self) -> None:
        if self._client:
            import asyncio
            try:
                asyncio.run(self._client.aclose())
            except Exception as exc:
                logger.error("Error closing LLM client: %s", exc)
            self._client = None
