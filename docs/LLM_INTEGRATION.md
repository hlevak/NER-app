# LLM Integration for NER-app

Этот документ описывает интеграцию LLM (LM Studio / llama.cpp) в NER-app для улучшенного распознавания сущностей, автоподсказок и нормализации в ансамбле со spaCy.

## Возможности

1. **Enhanced NER** — LLM как дополнительный источник сущностей с наивысшим приоритетом
2. **Normalization/Verification** — проверка и нормализация предсказанных сущностей
3. **Autocomplete** — подсказки при частичном вводе текста

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    CombinedNERBackend                        │
├─────────────────────────────────────────────────────────────┤
│  LLM (highest priority) → WebAPI → spaCy (lowest priority)  │
└─────────────────────────────────────────────────────────────┘
```

Приоритет в ансамбле: **LLM > WebAPI > spaCy**

## Настройка

### 1. Конфигурация через environment variables

Отредактируйте файл `config/ml-backend.env`:

```env
# LLM integration (LM Studio / llama.cpp)
LLM_ENABLED=true
LLM_PROVIDER=lmstudio
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=                    # Оставьте пустым для LM Studio
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2048
LLM_TIMEOUT=30
LLM_MAX_RETRIES=2
LLM_RETRY_DELAY=1.0
```

### 2. Провайдеры LLM

#### LM Studio (рекомендуется для локального использования)

1. Установите [LM Studio](https://lmstudio.ai/)
2. Загрузите модель (например, `mistral-7b-instruct-v0.2`)
3. Запустите локальный сервер (по умолчанию на `http://localhost:1234`)

```env
LLM_PROVIDER=lmstudio
LLM_BASE_URL=http://localhost:1234/v1
```

#### llama.cpp HTTP Server

1. Установите llama-cpp-python:
```bash
pip install llama-cpp-python
```

2. Запустите HTTP сервер:
```bash
python -m llama_cpp.server --model model.gguf --host localhost --port 8000
```

3. Настройте:
```env
LLM_PROVIDER=llamacpp
LLM_BASE_URL=http://localhost:8000/v1
```

#### OpenAI Compatible API

Для любого OpenAI-compatible API:

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=gpt-4
LLM_ENABLED=true
```

### 3. Рекомендуемые модели для русского языка

- **mistral-7b-instruct-v0.2** — хорошо работает с NER
- **saiga-mistral-7b** — адаптирована для русского языка
- **ruGPT-3.5-13B** — российская модель
- **llama-3-8b-instruct** — универсальная модель

## API Endpoints

### Health Check
```bash
GET /health
```

Ответ:
```json
{
  "status": "ok",
  "webapi_configured": false,
  "llm_configured": true
}
```

### Autocomplete Suggestions
```bash
POST /suggestions
Content-Type: application/json

{
  "text": "Иван Иванов работает в компании Яндекс",
  "partial": "Иван",
  "context": ""
}
```

Ответ:
```json
{
  "suggestions": [
    {"text": "Иван Иванов", "label": "PER", "confidence": 0.95},
    {"text": "Яндекс", "label": "ORG", "confidence": 0.9}
  ]
}
```

### Entity Normalization
```bash
POST /normalize
Content-Type: application/json

{
  "text": "yandex",
  "label": "ORG"
}
```

Ответ:
```json
{
  "text": "yandex",
  "label": "ORG",
  "normalized_text": "Яндекс",
  "confidence": 0.98
}
```

## Логирование

LLM-операции логируются в отдельные файлы:
- `logs/llm.log` — основные операции
- `logs/llm_errors.log` — ошибки

## Производительность

- **LLM** — более медленный, но точный (30-60 секунд на запрос)
- **spaCy** — быстрый, локальный (миллисекунды)
- **WebAPI** — зависит от сети

Рекомендуется использовать LLM для:
- Верификации сомнительных сущностей
- Нормализации (приведение к канонической форме)
- Автоподсказок при ручной разметке

## Оффлайн-режим

Если LLM не настроен или недоступен:
- Система автоматически переключается на spaCy + WebAPI
- Не требуется интернет (при локальном LLM)

## Тестирование

Проверка конфигурации без запуска сервера:

```python
from ml_backend.llm_client import LLMClient

client = LLMClient()
print(f"Configured: {client.is_configured()}")

# Тест синхронного вызова
entities = client.predict_entities_sync("Иван работает в Яндексе.")
print(entities)
```
