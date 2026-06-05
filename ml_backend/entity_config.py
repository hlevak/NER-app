"""Runtime loader for config/entities.json.

Provides ALLOWED_LABELS and build_ner_system_prompt() used by llm_client
and regex_ner instead of hardcoded values.
"""
import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "entities.json"

_NER_PROMPT_HEADER = (
    "Ты - эксперт в распознавании именованных сущностей (NER).\n"
    "Твоя задача - найти и классифицировать сущности в тексте.\n\n"
    "Допустимые типы сущностей:\n"
)

_NER_PROMPT_FOOTER = (
    '\nОтветь строго в формате JSON:\n'
    '{\n  "entities": [\n'
    '    {"label": "PER", "text": "Иван Иванов"},\n'
    '    {"label": "ES", "text": "Яндекс (www.ya.ru)"}\n'
    '  ]\n}\n\n'
    'Поле "text" должно содержать точную подстроку из исходного текста.\n'
    'Если сущностей нет, верни {"entities": []}.'
)


def _load() -> list[dict[str, Any]]:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"entities.json not found at {_CONFIG_PATH}. "
            "Run: python scripts/generate_input_schemas.py"
        )
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)["entities"]


ENTITIES: list[dict[str, Any]] = _load()
ALLOWED_LABELS: frozenset[str] = frozenset(e["label"] for e in ENTITIES)


def build_ner_system_prompt() -> str:
    lines: list[str] = []
    for ent in ENTITIES:
        line = f"- {ent['label']} ({ent['name_ru']}) - {ent['prompt_ru']}"
        lines.append(line)
    return _NER_PROMPT_HEADER + "\n".join(lines) + _NER_PROMPT_FOOTER
