# Архитектура NER-app

## Общая схема

```
┌─────────────────────────────────────────────────────────────┐
│                        Windows 10                           │
│                                                             │
│  ┌────────────────┐    HTTP/REST    ┌───────────────────┐   │
│  │  Label Studio  │◄──────────────►│   ML Backend      │   │
│  │  :8080         │                │   (Flask) :9090   │   │
│  │                │                │                   │   │
│  │  - Разметка    │                │  ┌─────────────┐  │   │
│  │  - Управление  │                │  │ SpacyNER    │  │   │
│  │  - Экспорт     │                │  │ Model       │  │   │
│  └───────┬────────┘                │  └──────┬──────┘  │   │
│          │                         │         │          │   │
│          │ SQLAlchemy              │  ┌──────▼──────┐  │   │
│          │                         │  │ WebAPI      │  │   │
│  ┌───────▼────────┐                │  │ Client      │  │   │
│  │  PostgreSQL    │                │  └─────────────┘  │   │
│  │  :5432         │                │                   │   │
│  │                │                │  ┌─────────────┐  │   │
│  │  label_studio  │                │  │ Model       │  │   │
│  │  database      │                │  │ Trainer     │  │   │
│  └────────────────┘                │  └─────────────┘  │   │
│                                    └───────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Файловая система                                    │   │
│  │  models/fine_tuned/  logs/  data/  wheels/           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                     (опционально)
                              │
                    ┌─────────▼──────────┐
                    │  Внешний WebAPI    │
                    │  (поиск сущностей) │
                    └────────────────────┘
```

## Компоненты

### Label Studio (порт 8080)

Веб-платформа для аннотации данных.

**Роль в системе:**
- Хранит тексты и разметку в PostgreSQL
- Предоставляет UI для разметчиков
- Отправляет тексты в ML Backend для предварительной разметки
- Запускает дообучение модели при накоплении аннотаций

**Конфигурация:** `config/label-studio.env`

### PostgreSQL (порт 5432)

Реляционная СУБД для Label Studio.

**Роль в системе:**
- Хранит проекты, задачи, аннотации, пользователей
- Обеспечивает транзакционность операций

**База данных:** `label_studio`  
**Пользователь:** `label_studio_user`

### ML Backend (порт 9090)

Flask-сервис, реализующий label-studio-ml интерфейс.

**Роль в системе:**
- Получает тексты из Label Studio через `/predict`
- Возвращает автоматическую NER-разметку
- Обучает/дообучает модель через `/fit`

**Конфигурация:** `config/ml-backend.env`

## Поток данных

### Предсказание (Predict)

```
1. Разметчик открывает задачу в Label Studio
2. Label Studio POST /predict → ML Backend
3. ML Backend:
   a. spaCy обрабатывает текст → список сущностей
   b. (опционально) WebAPI поиск → список сущностей
   c. Сущности объединяются (WebAPI имеет приоритет)
4. ML Backend возвращает результат в формате Label Studio
5. Label Studio показывает предварительную разметку разметчику
6. Разметчик корректирует и сохраняет
```

### Дообучение (Fine-tuning)

```
1. Накапливаются размеченные задачи в Label Studio
2. Ручной или автоматический запуск: POST /fit
3. ML Backend:
   a. parse_label_studio_annotations() - парсинг JSON
   b. Фильтрация перекрывающихся сущностей
   c. train_spacy_model() - дообучение NER
   d. Сохранение чекпоинтов
   e. Загрузка лучшей модели
4. Новые predict используют дообученную модель
```

## Модули ML Backend

```
ml_backend/
├── wsgi.py              # Точка входа Flask приложения
│   └── create_app()     # Инициализация через label_studio_ml
│
├── combined_ner_backend.py    # LabelStudioMLBase наследник
│   ├── predict()              # Предсказание для Label Studio
│   ├── fit()                  # Дообучение из Label Studio
│   ├── _merge_entities()      # Объединение spaCy + WebAPI
│   └── _entities_to_ls_result() # Конвертация формата
│
├── spacy_ner_model.py        # spaCy NER обёртка
│   ├── __init__()            # Загрузка модели
│   ├── predict()             # NER предсказание
│   ├── fit()                 # Дообучение
│   └── fit_from_label_studio() # С парсингом LS формата
│
├── model_trainer.py          # Логика обучения
│   ├── train_spacy_model()   # Основная функция обучения
│   ├── parse_label_studio_annotations() # Парсер JSON
│   └── _filter_overlapping_entities()  # Фильтрация
│
├── webapi_client.py          # HTTP клиент WebAPI
│   ├── search_entities()     # Поиск сущностей
│   └── normalize_entity()    # Нормализация
│
├── base_model.py    # Абстрактный базовый класс
└── logger.py        # Настройка логирования
```

## Слияние сущностей (Merge Strategy)

```
spaCy results:  [PER(0,5), LOC(15,21), ORG(25,30)]
WebAPI results: [PER(0,6), DATE(35,42)]

Merge:
  1. Берём все WebAPI сущности: [PER(0,6), DATE(35,42)]
  2. Для каждой spaCy сущности:
     - Если нет пересечения с WebAPI → добавляем
     - Если есть пересечение → пропускаем (WebAPI имеет приоритет)
  3. Результат: [PER(0,6), LOC(15,21), ORG(25,30), DATE(35,42)]
                  ↑ из WebAPI  ↑ из spaCy   ↑ из spaCy  ↑ из WebAPI
```

## Хранение моделей

```
models/
└── fine_tuned/
    ├── model_final/         ← загружается при старте (если есть)
    │   ├── config.cfg
    │   ├── meta.json
    │   └── ...
    ├── checkpoint_iter_025/ ← лучший по loss
    ├── checkpoint_epoch_010/
    └── checkpoint_epoch_020/
```

Приоритет загрузки:
1. `models/fine_tuned/model_final` (дообученная)
2. `ru_core_news_sm` или `ru_core_news_lg` (базовая)

## Логирование

```
logs/
├── app.log          # Общие события
├── app_errors.log   # Ошибки приложения (ERROR+)
├── predict.log      # Predict операции
├── fit.log          # Fit операции
├── webapi.log       # WebAPI вызовы
├── webapi_errors.log # Ошибки WebAPI (ERROR+)
└── training.log     # Процесс обучения
```

Ротация: 10 MB × 5 файлов = максимум 50 MB на каждый лог.

## Конфигурация

```
config/
├── label-studio.env     # Настройки Label Studio + PostgreSQL
├── ml-backend.env       # Настройки ML Backend + WebAPI
└── postgresql-init.sql  # SQL инициализация БД
```
