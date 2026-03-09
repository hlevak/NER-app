# ML Backend: Описание и API

## Обзор

ML Backend — Flask-сервис, реализующий интеграцию Label Studio с NER-моделями.

**Компоненты:**
- `combined_ner_backend.py` — основной backend (наследует `LabelStudioMLBase`)
- `spacy_ner_model.py` — обёртка над spaCy NER
- `webapi_client.py` — клиент внешнего WebAPI
- `model_trainer.py` — логика дообучения
- `logger.py` — конфигурация логирования

## API Endpoints

### GET /health

Проверка состояния сервиса.

```bash
curl http://localhost:9090/health
```

```json
{"status": "UP", "model_class": "CombinedNERBackend"}
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
          "score": 1.0
        }
      ],
      "score": 0.9
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
| `logs/training.log` | Процесс дообучения |

Ротация логов: 10 MB, хранится 5 файлов.

## Приоритет модели

1. При старте проверяется наличие дообученной модели `models/fine_tuned/model_final`
2. Если дообученная модель существует — загружается она
3. Иначе загружается базовая модель (`ru_core_news_sm` или `ru_core_news_lg`)
4. После успешного дообучения модель автоматически перезагружается

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
| `LOG_LEVEL` | `INFO` | Уровень логирования |
