# 🏷️ NER-app

[![Python](https://img.shields.io/badge/Python-3.10%2F3.11-blue.svg)](https://www.python.org/)
[![spaCy](https://img.shields.io/badge/spaCy-3.7.2+-green.svg)](https://spacy.io/)
[![Label Studio](https://img.shields.io/badge/Label_Studio-1.22.0-orange.svg)](https://labelstudio.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

> **NER-app** — система для разметки и распознавания именованных сущностей (Named Entity Recognition) на русском языке. Объединяет Label Studio, PostgreSQL и spaCy NER с возможностью дообучения моделей.

## 📋 Описание проекта

NER-app представляет собой полноценную платформу для:

- ⭐ **Разметки текстов** — интуитивный веб-интерфейс Label Studio для аннотации данных
- 🤖 **Автоматического распознавания сущностей** — spaCy NER модель с предсказаниями в реальном времени
- 🔗 **Интеграции с внешними WebAPI** — дополнительный поиск сущностей через сторонние сервисы
- 📈 **Дообучения моделей** — улучшение качества распознавания на размеченных данных
- 📝 **Логирования всех операций** — полный контроль над процессом работы системы

### Поддерживаемые типы сущностей

| Метка | Описание | Пример |
|-------|----------|--------|
| `PER` | Персоны | Иван Петров, Мария Сидорова |
| `ORG` | Организации | Яндекс, Google, Сбербанк |
| `LOC` | Локации | Москва, Россия, Эверест |
| `DATE` | Даты | 1 января 2024, вчера |
| `MISC` | Прочие сущности | UTF-8, iPhone 15 |

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Windows 10                                   │
│                                                                         │
│   ┌────────────────┐              HTTP/REST              ┌───────────┐  │
│   │ Label Studio  │◄───────────────────────────────────►│ ML Backend│  │
│   │   :8080       │                                   │  :9090     │  │
│   │               │                                   │            │  │
│   │ • Разметка    │                                   │ ┌───────┐  │  │
│   │ • Управление  │                                   │ │ spaCy │  │  │
│   │ • Экспорт    │                                   │ │  NER  │  │  │
│   └───────┬───────┘                                   │ └───┬───┘  │  │
│           │                                             │     │     │  │
│           │ SQLAlchemy                                 │ ┌───▼───┐  │  │
│   ┌───────▼───────┐                                     │ │WebAPI │  │  │
│   │  PostgreSQL   │                                     │ │Client │  │  │
│   │    :5432      │                                     │ └───────┘  │  │
│   │                │                                   │            │  │
│   │ label_studio   │                                   │ ┌───────┐  │  │
│   │   database    │                                   │ │ Model │  │  │
│   └────────────────┘                                   │ │Trainer│  │  │
│                                                         │ └───────┘  │  │
│                                                         └────────────┘  │
│   ┌──────────────────────────────────────────────────────────────┐    │
│   │                    Файловая система                           │    │
│   │   models/fine_tuned/   logs/   data/   wheels/   config/     │    │
│   └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                           (опционально)
                                    │
                    ┌───────────────▼────────────────┐
                    │      Внешний WebAPI            │
                    │   (поиск именованных сущностей) │
                    └────────────────────────────────┘
```

### Компоненты системы

| Компонент | Порт | Описание |
|-----------|------|----------|
| **Label Studio** | 8080 | Веб-платформа для аннотации данных с UI разметчика |
| **PostgreSQL** | 5432 | Реляционная СУБД для хранения проектов, задач и аннотаций |
| **ML Backend** | 9090 | Flask-сервис с spaCy NER + WebAPI клиент |

### Поток данных

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Предсказание (Predict)                            │
└────────────────────────────────────────────────────────────────────────┘

   Разметчик          Label Studio            ML Backend            spaCy/WebAPI
      │                    │                       │                       │
      │  1. Открывает      │                       │                       │
      │     задачу         │                       │                       │
      │───────►           │                       │                       │
      │                    │                       │                       │
      │                    │  2. POST /predict     │                       │
      │                    │──────────────────────►                       │
      │                    │                       │                       │
      │                    │                       │  3. NER анализ       │
      │                    │                       │──────────────────────►
      │                    │                       │                       │
      │                    │                       │  4. Сущности         │
      │                    │                       │◄──────────────────────
      │                    │                       │                       │
      │                    │  5. Результат LS      │                       │
      │                    │◄───────────────────────                       │
      │                    │                       │                       │
      │  6. Предсказанная │                       │                       │
      │     разметка       │                       │                       │
      │◄───────            │                       │                       │
      │                    │                       │                       │
```

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Дообучение (Fine-tuning)                           │
└────────────────────────────────────────────────────────────────────────┘

   Накопление         Label Studio            ML Backend
   аннотаций              │                       │
      │                   │                       │
      │  1. Экспорт       │                       │
      │◄───────           │                       │
      │                   │                       │
      │                   │  2. POST /fit         │
      │                   │──────────────────────►
      │                   │                       │
      │                   │  3. parse_label_studio
      │                   │      _annotations()   │
      │                   │                       │
      │                   │  4. train_spacy_model │
      │                   │      ()               │
      │                   │                       │
      │                   │  5. Сохранение        │
      │                   │      checkpoint       │
      │                   │                       │
      │                   │  6. Перезагрузка      │
      │                   │      модели           │
      │                   │                       │
```

---

## ✨ Функциональность

### Основные возможности

| Функция | Описание |
|---------|----------|
| 🏷️ **NER-разметка текстов** | Веб-интерфейс для ручной разметки именованных сущностей |
| 💡 **Автоподсказки** | Предварительная разметка от spaCy NER модели при открытии задачи |
| 🌐 **WebAPI интеграция** | Дополнительный поиск сущностей через внешний REST API |
| 📚 **Дообучение модели** | Улучшение качества распознавания на размеченных данных |
| 📋 **Логирование** | Полная история операций: predict, fit, WebAPI вызовы |
| 🔄 **Автообновление** | Автоматический перезапуск дообучения при накоплении аннотаций |

### Слияние результатов (Merge Strategy)

```
spaCy результаты:    [PER(0,5),    LOC(15,21), ORG(25,30)     ]
WebAPI результаты:   [PER(0,6),                      DATE(35,42)]

Объединение:
  1. Все WebAPI сущности сохраняются:  [PER(0,6), DATE(35,42)]
  2. spaCy сущности без пересечений:   [LOC(15,21), ORG(25,30)]
  
Итоговый результат:  [PER(0,6), LOC(15,21), ORG(25,30), DATE(35,42)]
                     ↑ WebAPI    ↑ spaCy      ↑ spaCy      ↑ WebAPI
```

> **Приоритет:** WebAPI имеет приоритет над spaCy при пересечении сущностей

---

## 📦 Требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **ОС** | Windows 10 x64 | Windows 10/11 x64 |
| **Python** | 3.10 | 3.11 |
| **RAM** | 4 GB | 8+ GB |
| **Disk** | 5 GB | 10+ GB |
| **CPU** | 4 cores | 8+ cores |
| **PostgreSQL** | 15+ | 15+ |

### Необходимое ПО

- 🐘 **PostgreSQL 15+** — https://www.postgresql.org/download/windows/
- 🐍 **Python 3.10/3.11** — https://www.python.org/downloads/windows/
- 🌐 **Label Studio 1.22.0** — устанавливается через pip

---

## 🚀 Быстрый старт

> Для пользователей, знакомых с системой. Полная инструкция в разделе [Установка](#-установка).

### Предварительные требования

1. ✅ PostgreSQL 15+ установлен
2. ✅ Python 3.10 или 3.11 установлен
3. ✅ Создана база данных `label_studio`

### Запуск

```bat
cd C:\NER-app

:: Активировать виртуальное окружение
venv\Scripts\activate

:: Запустить все сервисы
scripts\start_all.bat
```

### Доступ к сервисам

| Сервис | URL | Описание |
|--------|-----|----------|
| 🌐 **Label Studio** | http://localhost:8080 | Интерфейс разметки |
| ⚙️ **ML Backend** | http://localhost:9090/health | Проверка здоровья API |

### Первоначальная настройка Label Studio

1. Откройте http://localhost:8080
2. Создайте аккаунт администратора
3. Создайте проект **Named Entity Recognition**
4. Настройте шаблон разметки:
   ```xml
   <View>
     <Labels name="label" toName="text">
       <Label value="PER" background="#FFA39E"/>
       <Label value="ORG" background="#D4380D"/>
       <Label value="LOC" background="#FFC069"/>
       <Label value="DATE" background="#95DE64"/>
       <Label value="MISC" background="#5CDBD3"/>
     </Labels>
     <Text name="text" value="$text"/>
   </View>
   ```
5. Подключите ML Backend: **Settings → Machine Learning → Add Model**
   - URL: `http://localhost:9090`
   - Название: `spaCy NER Backend`

---

## 📥 Установка

### Вариант A: Online установка (с интернетом)

#### 1. Установка PostgreSQL

```bat
:: Скачайте с https://www.postgresql.org/download/windows/
:: Запустите установщик, запомните пароль пользователя postgres
```

#### 2. Инициализация базы данных

```bat
cd C:\NER-app
scripts\setup_database.bat
```

> При запросе введите пароль пользователя `postgres`

#### 3. Создание виртуального окружения

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 4. Настройка конфигурации

Отредактируйте файлы конфигурации:

**`config/label-studio.env`**
```env
POSTGRE_HOST=localhost
POSTGRE_PORT=5432
POSTGRE_PASSWORD=LabelStudio2024!
LABEL_STUDIO_HOST=http://localhost:8080
```

**`config/ml-backend.env`**
```env
SPACY_MODEL=ru_core_news_sm
MODELS_DIR=C:\NER-app\models
LOGS_DIR=C:\NER-app\logs
ML_BACKEND_PORT=9090
```

> ⚠️ **Обязательно смените пароли!**

#### 5. Запуск сервисов

```bat
scripts\start_all.bat
```

---

### Вариант B: Offline установка (изолированная машина)

Подробная инструкция: [docs/OFFLINE_SETUP.md](docs/OFFLINE_SETUP.md)

#### 1. Подготовка на машине с интернетом

```bat
:: Скачивание всех необходимых пакетов
scripts\download_wheels.bat

:: Для включения большой модели (опционально)
python scripts\download_wheels.py --include-lg-model
```

#### 2. Перенос на изолированную машину

Создайте архив, включающий:
```
transfer_package/
├── NER-app/wheels/     # Скачанные wheels
├── postgresql-*.exe    # Установщик PostgreSQL
└── (其余 файлы проекта)
```

#### 3. Установка на изолированной машине

```bat
:: Установка PostgreSQL
postgresql-*-windows-x64.exe

:: Запуск offline установки
scripts\install_offline.bat

:: Инициализация БД
scripts\setup_database.bat
```

#### 4. Запуск

```bat
scripts\start_all.bat
```

---

## ⚙️ Настройка ML Backend

### Подключение к Label Studio

1. Откройте **Settings → Machine Learning** в Label Studio
2. Нажмите **Add Model**
3. Заполните поля:
   - **URL**: `http://localhost:9090`
   - **Name**: `spaCy NER Backend`
   - **Description**: (опционально)
4. Нажмите **Validate and Save**

### Настройка WebAPI (опционально)

Добавьте в `config/ml-backend.env`:

```env
# WebAPI интеграция
WEBAPI_BASE_URL=http://your-api-server.com/api
WEBAPI_TOKEN=your-api-token
WEBAPI_TIMEOUT=10
WEBAPI_MAX_RETRIES=3
```

#### Ожидаемый формат ответа WebAPI

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

### Выбор spaCy модели

| Модель | Размер | Скорость | Точность |
|--------|--------|----------|----------|
| `ru_core_news_sm` | ~40 MB | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ |
| `ru_core_news_lg` | ~550 MB | ⚡⚡⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

```env
SPACY_MODEL=ru_core_news_sm  # Быстрая (по умолчанию)
# или
SPACY_MODEL=ru_core_news_lg  # Точная
```

---

## 📈 Дообучение модели

### Экспорт данных из Label Studio

1. Откройте проект в Label Studio
2. Перейдите **Export** → выберите **JSON**
3. Сохраните файл (например, `annotations.json`)

### Запуск дообучения

#### Способ 1: Через Label Studio (автоматически)

1. **Settings → Machine Learning → Edit Model**
2. Включите **Auto-update model**
3. Label Studio будет вызывать `/fit` автоматически

#### Способ 2: Через API (ручной запуск)

```python
import requests
import json

with open("annotations.json", encoding="utf-8") as f:
    tasks = json.load(f)

response = requests.post(
    "http://localhost:9090/fit",
    json={"annotations": tasks},
    timeout=300
)
print(response.json())
```

#### Способ 3: Скрипт командной строки

```bat
venv\Scripts\activate
python -c "
from ml_backend.spacy_ner_model import SpacyNERModel
import json

with open('annotations.json', encoding='utf-8') as f:
    tasks = json.load(f)

model = SpacyNERModel()
metrics = model.fit_from_label_studio(tasks)
print('Training metrics:', metrics)
"
```

### Оценка качества

После обучения `/fit` возвращает метрики:

```json
{
  "status": "success",
  "iterations": 30,
  "examples": 150,
  "best_loss": 0.0842,
  "best_checkpoint": "models/fine_tuned/checkpoint_iter_028",
  "final_model": "models/fine_tuned/model_final",
  "elapsed_seconds": 127.4
}
```

### Переключение на новую модель

После успешного дообучения модель автоматически загружается при следующем запросе `/predict`.

### Откат к базовой модели

```bat
:: Удалить дообученную модель
rmdir /s /q models\fine_tuned\model_final

:: Перезапустить ML Backend - загрузит базовую модель
scripts\start_ml_backend.bat
```

### Рекомендации по разметке

| Тип сущности | Минимум | Рекомендуется |
|-------------|---------|---------------|
| PER (персоны) | 50 | 200+ |
| ORG (организации) | 50 | 200+ |
| LOC (локации) | 50 | 200+ |
| DATE (даты) | 30 | 100+ |

---

## 📁 Структура проекта

```
NER-app/
├── .gitignore                  # Git игнорируемые файлы
├── README.md                    # Этот файл
├── requirements.txt             # Зависимости Python
├── requirements-build.txt       # Зависимости сборки
│
├── config/                      # Конфигурационные файлы
│   ├── label-studio.env         # Настройки Label Studio + PostgreSQL
│   ├── ml-backend.env           # Настройки ML Backend + WebAPI
│   └── postgresql-init.sql      # SQL инициализация БД
│
├── ml_backend/                  # ML Backend исходный код
│   ├── __init__.py
│   ├── wsgi.py                  # Точка входа Flask приложения
│   ├── combined_ner_backend.py  # LabelStudioMLBase наследник
│   ├── spacy_ner_model.py       # spaCy NER обёртка
│   ├── model_trainer.py         # Логика обучения
│   ├── webapi_client.py        # HTTP клиент WebAPI
│   ├── base_model.py           # Абстрактный базовый класс
│   ├── logger.py               # Настройка логирования
│   └── requirements.txt        # Зависимости ML Backend
│
├── scripts/                     # Скрипты запуска (Windows batch)
│   ├── start_all.bat           # Запуск всех сервисов
│   ├── start_ml_backend.bat   # Запуск ML Backend
│   ├── start_label_studio.bat # Запуск Label Studio
│   ├── setup_database.bat     # Настройка PostgreSQL
│   ├── install_offline.bat    # Offline установка
│   ├── download_wheels.py     # Скачивание wheels
│   └── download_wheels.bat    # Скачивание wheels (batch)
│
├── docs/                       # Документация
│   ├── ARCHITECTURE.md         # Архитектура системы
│   ├── INSTALLATION.md         # Инструкция по установке
│   ├── OFFLINE_SETUP.md        # Offline установка
│   ├── ML_BACKEND.md           # Описание ML Backend API
│   ├── MODEL_TRAINING.md       # Дообучение модели
│   └── TROUBLESHOOTING.md      # Устранение проблем
│
├── models/                     # Хранение моделей
│   └── fine_tuned/             # Дообученные модели
│       ├── model_final/        # Активная дообученная модель
│       └── checkpoint_*/       # Чекпоинты обучения
│
├── logs/                       # Лог-файлы
│   ├── app.log                 # Общие события
│   ├── app_errors.log          # Ошибки приложения (ERROR+)
│   ├── predict.log             # Predict операции
│   ├── fit.log                 # Fit операции
│   ├── webapi.log              # WebAPI вызовы
│   ├── webapi_errors.log       # Ошибки WebAPI
│   └── training.log             # Процесс обучения
│
└── wheels/                     # Wheel-пакеты для offline установки
```

---

## 🔌 API Reference

### GET /health

Проверка состояния сервиса.

```bash
curl http://localhost:9090/health
```

**Ответ:**
```json
{"status": "UP", "model_class": "CombinedNERBackend"}
```

---

### POST /predict

Получение предсказаний NER.

```bash
curl -X POST http://localhost:9090/predict \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"data": {"text": "Иван Петров работает в Яндексе в Москве."}}
    ]
  }'
```

**Ответ:**
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
        },
        {
          "from_name": "label",
          "to_name": "text",
          "type": "labels",
          "value": {
            "start": 26,
            "end": 32,
            "text": "Яндексе",
            "labels": ["ORG"]
          },
          "score": 0.95
        }
      ],
      "score": 0.92
    }
  ]
}
```

---

### POST /fit

Запуск дообучения модели.

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
              {"type": "labels", "value": {"start": 0, "end": 5, "labels": ["PER"]}},
              {"type": "labels", "value": {"start": 16, "end": 22, "labels": ["LOC"]}}
            ]
          }
        ]
      }
    ]
  }'
```

**Ответ:**
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

---

## 📝 Логирование

### Расположение логов

Все логи находятся в директории `logs/`:

| Файл | Описание | Уровень |
|------|----------|---------|
| `app.log` | Общие события приложения | INFO |
| `app_errors.log` | Ошибки приложения | ERROR |
| `predict.log` | Все вызовы `/predict` | DEBUG |
| `fit.log` | Все вызовы `/fit` | DEBUG |
| `webapi.log` | Обращения к WebAPI | INFO |
| `webapi_errors.log` | Ошибки WebAPI | ERROR |
| `training.log` | Процесс дообучения | INFO |

### Настройка логирования

В `config/ml-backend.env`:

```env
LOG_LEVEL=INFO              # Уровень логирования
LOG_MAX_BYTES=10485760     # 10 MB (макс размер файла)
LOG_BACKUP_COUNT=5          # Количество резервных копий
```

### Просмотр логов

```bat
:: Последние ошибки
type logs\app_errors.log

:: Предсказания
type logs\predict.log

:: Процесс обучения
type logs\training.log

:: WebAPI ошибки
type logs\webapi_errors.log
```

---

## 🔧 Troubleshooting

Подробная документация: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

### Частые проблемы

#### ❌ Ошибки подключения к PostgreSQL

```bat
:: Проверка статуса PostgreSQL
sc query postgresql-x64-15

:: Запуск службы
net start postgresql-x64-15

:: Проверка подключения
psql -U label_studio_user -h localhost -d label_studio
```

**Решение:** Проверьте параметры в `config/label-studio.env`:
- `POSTGRE_HOST` — обычно `localhost`
- `POSTGRE_PORT` — обычно `5432`
- `POSTGRE_PASSWORD` — должен совпадать с паролем при инициализации БД

---

#### ❌ Проблемы с ML Backend

**spaCy модель не найдена:**
```bat
venv\Scripts\activate
pip install wheels\ru_core_news_sm-3.7.0-py3-none-any.whl
python -m spacy link ru_core_news_sm ru
```

**ML Backend не отвечает:**
```bat
:: Проверка здоровья
curl http://localhost:9090/health

:: Просмотр логов
type logs\app_errors.log
```

---

#### ❌ Ошибки WebAPI

**Симптом:** `WEBAPI_TIMEOUT` или ошибки подключения

**Решение:**
1. Проверьте URL и токен в `config/ml-backend.env`
2. Проверьте логи: `logs/webapi_errors.log`
3. Временно отключите WebAPI: очистите `WEBAPI_BASE_URL`

---

#### ❌ Медленная работа

**Решения:**
1. Используйте `ru_core_news_sm` вместо `ru_core_news_lg`
2. Уменьшите размер батча в Label Studio
3. Отключите WebAPI (уберите `WEBAPI_BASE_URL`)
4. Уменьшите `TRAINING_ITERATIONS` до 10-15

---

### Диагностические команды

```bat
:: Проверка версий
venv\Scripts\activate
python -m spacy info
python -c "import label_studio_ml; print(label_studio_ml.__version__)"
psql --version

:: Тест ML Backend
curl -X POST http://localhost:9090/predict -H "Content-Type: application/json" -d "{\"tasks\":[{\"data\":{\"text\":\"Тест\"}}]}"

:: Тест spaCy
python -c "import spacy; nlp = spacy.load('ru_core_news_sm'); print([(e.text, e.label_) for e in nlp('Москва — столица России').ents])"
```

---

## 🔨 Разработка

### Расширение функциональности

#### Добавление нового типа сущности

1. Добавьте метку в шаблон Label Studio:
   ```xml
   <Label value="NEW_ENTITY" background="#FF0000"/>
   ```

2. Обновите дообученную модель с новыми примерами

#### Интеграция нового WebAPI

Отредактируйте `ml_backend/webapi_client.py`:

```python
def search_entities(self, text: str) -> List[Dict]:
    """Интеграция с новым API"""
    response = self.session.post(
        f"{self.base_url}/ner",
        json={"text": text},
        headers={"Authorization": f"Bearer {self.token}"},
        timeout=self.timeout
    )
    return response.json().get("entities", [])
```

#### Добавление новой spaCy модели

1. Скачайте модель: `python -m spacy download en_core_web_sm`
2. Обновите `config/ml-backend.env`: `SPACY_MODEL=en_core_web_sm`

### Тестирование

```bat
venv\Scripts\activate

:: Запуск unit тестов
pytest tests/

:: Тестирование конкретного модуля
python -m pytest tests/test_spacy_ner_model.py -v
```

---

## 📄 Лицензия

MIT License

Copyright © 2024 NER-app

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 📚 Дополнительная документация

| Документ | Описание |
|----------|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Подробная архитектура системы |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Полная инструкция по установке |
| [docs/OFFLINE_SETUP.md](docs/OFFLINE_SETUP.md) | Установка без интернета |
| [docs/ML_BACKEND.md](docs/ML_BACKEND.md) | Детальное описание API ML Backend |
| [docs/MODEL_TRAINING.md](docs/MODEL_TRAINING.md) | Дообучение и оптимизация модели |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Решение проблем |

---

<div align="center">

**NER-app** — Сделано с ❤️ для сообщества NLP

</div>
