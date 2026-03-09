# Дообучение (Fine-tuning) spaCy модели

## Обзор процесса

```
Label Studio (разметка)
    │
    ▼
Экспорт JSON
    │
    ▼
POST /fit  ──► parse_label_studio_annotations()
    │
    ▼
train_spacy_model()
    │
    ├──► checkpoint_iter_001/  (лучший чекпоинт)
    ├──► checkpoint_iter_010/  (периодический)
    └──► model_final/          (финальная модель)
    │
    ▼
Автоматическая перезагрузка модели
    │
    ▼
Новые predict используют дообученную модель
```

## Способы запуска дообучения

### Способ 1: Через Label Studio (автоматически)

Label Studio может автоматически запускать дообучение после накопления аннотаций:

1. Settings → Machine Learning → Edit Model
2. Включите "Auto-update model"
3. Label Studio будет вызывать `/fit` после каждой аннотации или пакетами

### Способ 2: Через API (ручной запуск)

Экспортируйте данные из Label Studio (формат JSON) и отправьте POST-запрос:

```python
import requests
import json

# Загрузка экспортированных данных
with open("export.json", encoding="utf-8") as f:
    tasks = json.load(f)

response = requests.post(
    "http://localhost:9090/fit",
    json={"annotations": tasks},
    timeout=300
)
print(response.json())
```

### Способ 3: Скрипт командной строки

```bat
venv\Scripts\activate
python -c "
from ml_backend.spacy_ner_model import SpacyNERModel
import json

with open('export.json', encoding='utf-8') as f:
    tasks = json.load(f)

model = SpacyNERModel()
metrics = model.fit_from_label_studio(tasks)
print('Training metrics:', metrics)
"
```

## Формат данных Label Studio

ML Backend ожидает стандартный экспорт Label Studio в JSON:

```json
[
  {
    "id": 1,
    "data": {
      "text": "Путин встретился с Байденом в Женеве."
    },
    "annotations": [
      {
        "result": [
          {
            "type": "labels",
            "value": {
              "start": 0,
              "end": 5,
              "text": "Путин",
              "labels": ["PER"]
            }
          },
          {
            "type": "labels",
            "value": {
              "start": 18,
              "end": 25,
              "text": "Байденом",
              "labels": ["PER"]
            }
          },
          {
            "type": "labels",
            "value": {
              "start": 28,
              "end": 34,
              "text": "Женеве",
              "labels": ["LOC"]
            }
          }
        ]
      }
    ]
  }
]
```

## Параметры обучения

Настраиваются через `config/ml-backend.env`:

```env
TRAINING_ITERATIONS=30    # Количество эпох
TRAINING_DROPOUT=0.3      # Dropout (0.0-0.5)
```

Дополнительные параметры в коде `model_trainer.py`:

```python
train_spacy_model(
    nlp=nlp,
    training_data=data,
    output_dir=output_dir,
    n_iter=30,              # Количество итераций
    drop=0.3,               # Dropout
    batch_size_start=4.0,   # Начальный размер батча
    batch_size_end=32.0,    # Конечный размер батча
    checkpoint_every=10,    # Периодические чекпоинты
)
```

## Чекпоинты (Checkpoints)

Сохраняются автоматически в `models/fine_tuned/`:

```
models/fine_tuned/
├── checkpoint_iter_025/  ← лучший чекпоинт (min NER loss)
├── checkpoint_epoch_010/ ← периодический чекпоинт
├── checkpoint_epoch_020/ ← периодический чекпоинт
└── model_final/          ← финальная модель (загружается при старте)
```

### Ручная загрузка чекпоинта

```python
from ml_backend.spacy_ner_model import SpacyNERModel

model = SpacyNERModel()
model.load("models/fine_tuned/checkpoint_iter_025")
model.save("models/fine_tuned/model_final")
```

## Рекомендации по разметке

### Минимальный датасет

| Тип сущности | Минимум примеров | Рекомендуется |
|-------------|-----------------|--------------|
| PER (персоны) | 50 | 200+ |
| ORG (организации) | 50 | 200+ |
| LOC (локации) | 50 | 200+ |
| DATE (даты) | 30 | 100+ |

### Качество разметки

- Размечайте **все** вхождения сущностей в тексте
- Используйте **консистентные** метки (не смешивайте PER/PERSON)
- Избегайте перекрывающихся сущностей (перекрытия отфильтровываются автоматически)
- Балансируйте классы — избыток одного класса снижает качество других

### Итеративное улучшение

1. Разметьте 100-200 примеров
2. Запустите дообучение (`/fit`)
3. Проверьте качество предсказаний на новых текстах
4. Исправьте ошибки, добавьте сложные случаи
5. Повторите с шага 2

## Метрики обучения

После дообучения `/fit` возвращает:

```json
{
  "status": "success",
  "iterations": 30,
  "examples": 150,
  "best_loss": 0.0842,
  "best_checkpoint": "models/fine_tuned/checkpoint_iter_028",
  "final_model": "models/fine_tuned/model_final",
  "elapsed_seconds": 127.4,
  "losses_history": [
    {"iteration": 1, "ner_loss": 2.3141},
    {"iteration": 2, "ner_loss": 1.8923},
    ...
    {"iteration": 30, "ner_loss": 0.1034}
  ]
}
```

Мониторинг обучения в реальном времени: `logs/training.log`

## Откат к базовой модели

Если дообученная модель работает хуже:

```bat
REM Удалить дообученную модель
rmdir /s /q models\fine_tuned\model_final

REM Перезапустить ML Backend - загрузит базовую модель
scripts\start_ml_backend.bat
```
