# ML Backend: Описание и API

## Обзор

ML Backend — Flask-сервис, реализующий интеграцию Label Studio с NER-моделями.

**Компоненты:**
- `combined_ner_backend.py` — основной backend (наследует `LabelStudioMLBase`)
- `spacy_ner_model.py` — обёртка над spaCy NER
- `webapi_client.py` — клиент внешнего WebAPI
- `llm_client.py` — клиент LLM (LM Studio / llama.cpp)
- `model_trainer.py` — логика дообучения
- `logger.py` — конфигурация логирования
- `wsgi.py` — точка входа Flask приложения

## Запуск

### Запуск через Flask (рекомендуется)

```bash
# Перейти в директорию проекта
cd /path/to/NER-app

# Активировать виртуальное окружение
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Запуск через скрипт
./scripts/start_ml_backend.sh  # Linux/macOS
# или
scripts\start_ml_backend.bat    # Windows
```

### Запуск напрямую через Python

```bash
python -m ml_backend.wsgi
```

### Переменные окружения

| Переменная | По умолчанию | Описание |
|-----------|-------------|---------|
| `ML_BACKEND_HOST` | `0.0.0.0` | Хост сервера |
| `ML_BACKEND_PORT` | `9090` | Порт сервера |
| `FLASK_DEBUG` | `false` | Режим отладки |
| `SPACY_MODEL` | `ru_core_news_sm` | Имя базовой spaCy модели |
| `MODELS_DIR` | `../models` | Директория для сохранения моделей |
| `LOGS_DIR` | `../logs` | Директория для логов |

## API Endpoints

### GET /health

Проверка состояния сервиса.

```bash
curl http://localhost:9090/health
```

```json
{
  "status": "ok",
  "webapi_configured": false,
  "llm_configured": false
}
```

### POST /setup

Инициализация и получение информации о возможностях ML Backend.

```bash
curl -X POST http://localhost:9090/setup \
  -H "Content-Type: application/json"
```

```json
{
  "status": "ok",
  "model_class": "CombinedNERBackend",
  "supported_modes": ["pre-annotation", "interactive", "training"],
  "capabilities": {
    "predict": true,
    "fit": true,
    "interactive": true,
    "suggestions": true
  },
  "webapi_configured": false,
  "llm_configured": false
}
```

### POST /predict

Получение предсказаний NER для задач из Label Studio.

```bash
curl -X POST http://localhost:9090/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"data": {"text": "Иван Петров работает в компании Яндекс в Москве."}}
    ]
  }'
```

```json
{
  "results": [
    {
      "result": [
        {
          "from_name": "label",
          "to_name": "text",
          "type": "labels",
          "value": {
            "start": 0,
            "end": 11,
            "text": "Иван Петров",
            "labels": ["PER"]
          },
          "score": 0.95,
          "meta": {
            "source": "spacy",
            "reasoning": "Имя человека: 'Иван Петров' - распознано как персоналия"
          }
        },
        {
          "from_name": "label",
          "to_name": "text",
          "type": "labels",
          "value": {
            "start": 35,
            "end": 40,
            "text": "Яндекс",
            "labels": ["ORG"]
          },
          "score": 0.94,
          "meta": {
            "source": "spacy",
            "reasoning": "Организация: 'Яндекс' - распознано как компания или учреждение"
          }
        }
      ],
      "score": 0.945
    }
  ]
}
```

### POST /fit

Запуск дообучения модели на размеченных данных.

```bash
curl -X POST http://localhost:9090/fit \
  -H "Content-Type: application/json" \
  -d '{
    "annotations": [
      {
        "data": {"text": "Путин выступил в Кремле."},
        "annotations": [
          {
            "result": [
              {
                "type": "labels",
                "value": {"start": 0, "end": 5, "labels": ["PER"]}
              },
              {
                "type": "labels",
                "value": {"start": 16, "end": 22, "labels": ["LOC"]}
              }
            ]
          }
        ]
      }
    ]
  }'
```

```json
{
  "status": "success",
  "iterations": 30,
  "examples": 1,
  "best_loss": 0.1234,
  "best_checkpoint": "models/fine_tuned/checkpoint_iter_025",
  "final_model": "models/fine_tuned/model_final",
  "elapsed_seconds": 45.2
}
```

### POST /interactive

Интерактивный режим для получения предсказаний в реальном времени.

```bash
curl -X POST http://localhost:9090/interactive \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Иван Петров работает в Яндексе.",
    "context": ""
  }'
```

```json
{
  "result": [...],
  "suggestions": [],
  "score": 0.95
}
```

### POST /suggestions

Получение подсказок для автодополнения.

```bash
curl -X POST http://localhost:9090/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Иван Петров работает в компании Яндекс",
    "partial": "Янд",
    "context": ""
  }'
```

```json
{
  "suggestions": [
    {
      "text": "Яндекс",
      "label": "ORG",
      "confidence": 0.9
    }
  ]
}
```

### POST /normalize

Нормализация/верификация сущности.

```bash
curl -X POST http://localhost:9090/normalize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Яндекс",
    "label": "ORG"
  }'
```

```json
{
  "text": "Яндекс",
  "label": "ORG",
  "normalized_text": "Яндекс",
  "confidence": 1.0
}
```

## WebAPI интеграция

ML Backend может обращаться к внешнему WebAPI для получения дополнительных сущностей.

### Настройка

В `config/ml-backend.env`:
```
WEBAPI_BASE_URL=http://your-api-server.com/api
WEBAPI_TOKEN=your-api-token
WEBAPI_TIMEOUT=10
WEBAPI_MAX_RETRIES=3
```

### Ожидаемый формат ответа WebAPI

```json
{
  "entities": [
    {
      "start": 0,
      "end": 11,
      "label": "PER",
      "text": "Иван Петров",
      "score": 0.95
    }
  ]
}
```

### Fallback поведение

При недоступности WebAPI (таймаут, ошибка соединения) бэкенд автоматически использует только spaCy. Ошибки WebAPI записываются в `logs/webapi_errors.log`.

## Логирование

| Файл | Содержимое |
|------|-----------|
| `logs/app.log` | Общие события приложения |
| `logs/app_errors.log` | Ошибки приложения |
| `logs/predict.log` | Все вызовы /predict |
| `logs/fit.log` | Все вызовы /fit |
| `logs/webapi.log` | Обращения к WebAPI |
| `logs/webapi_errors.log` | Ошибки WebAPI |
| `logs/llm.log` | Обращения к LLM |
| `logs/llm_errors.log` | Ошибки LLM |
| `logs/training.log` | Процесс дообучения |

Ротация логов: 10 MB, хранится 5 файлов.

## Приоритет модели

1. При старте проверяется наличие дообученной модели `models/fine_tuned/model_final`
2. Если дообученная модель существует — загружается она
3. Иначе загружается базовая модель (`ru_core_news_sm` или `ru_core_news_lg`)
4. После успешного дообучения модель автоматически перезагружается

## Confidence и Reasoning

Каждая сущность в ответе содержит:
- **`score`** - уверенность модели (0.0 - 1.0)
- **`meta.source`** - источник сущности (spacy, webapi, llm)
- **`meta.reasoning`** - текстовое объяснение классификации

### Расчет confidence

- **spaCy**: 0.85 - 0.99 (базовая + бонусы за длину и регистр)
- **WebAPI**: как предоставлено внешним API (или 0.85 по умолчанию)
- **LLM**: как оценил сам LLM (или 0.9 по умолчанию)

### Объяснения (reasoning)

Генерируются автоматически на основе:
- Типа сущности (PER, ORG, LOC, etc.)
- Текста сущности
- Источника данных

## Режимы работы

### Pre-annotation

Автоматическая разметка при создании задач:
1. Загрузите данные в Label Studio
2. ML Backend автоматически создает предварительные аннотации
3. Разметчик проверяет и корректирует

### Interactive Mode

Реальные предсказания во время редактирования:
1. Включите в настройках ML Backend **Use for interactive pre-annotation**
2. При открытии задачи автоматически загружаются предсказания
3. При изменении текста можно получить новые предсказания

### Training

Дообучение на размеченных данных:
1. Включите **Auto-update model** в настройках ML Backend
2. Label Studio будет вызывать `/fit` при накоплении аннотаций
3. Или вызовите `/fit` вручную через API

## Переменные окружения

| Переменная | По умолчанию | Описание |
|-----------|-------------|---------|
| `SPACY_MODEL` | `ru_core_news_sm` | Имя базовой spaCy модели |
| `MODELS_DIR` | `../models` | Директория для сохранения моделей |
| `LOGS_DIR` | `../logs` | Директория для логов |
| `TRAINING_ITERATIONS` | `30` | Количество итераций обучения |
| `TRAINING_DROPOUT` | `0.3` | Dropout при обучении |
| `ML_BACKEND_HOST` | `0.0.0.0` | Хост сервера |
| `ML_BACKEND_PORT` | `9090` | Порт сервера |
| `WEBAPI_BASE_URL` | `` | URL WebAPI (пусто = отключено) |
| `WEBAPI_TOKEN` | `` | Токен авторизации WebAPI |
| `WEBAPI_TIMEOUT` | `10` | Таймаут WebAPI запросов (сек) |
| `LLM_ENABLED` | `false` | Включить LLM интеграцию |
| `LLM_BASE_URL` | `http://localhost:1234/v1` | URL LLM сервера |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
