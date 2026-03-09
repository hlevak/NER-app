# Offline Установка NER-app

Инструкция по переносу и установке на изолированной машине без интернета.

## Шаг 1: Подготовка на машине с интернетом

### 1.1 Требования

- Windows 10 x64
- Python 3.10 или 3.11 (такая же версия, как на целевой машине)
- Интернет-соединение

### 1.2 Скачивание wheels

```bat
cd C:\NER-app
scripts\download_wheels.bat
```

Для Python 3.10:
```bat
scripts\download_wheels.bat --python-version 3.10
```

Для включения большой модели (ru_core_news_lg, ~550MB):
```bat
python scripts\download_wheels.py --python-version 3.11 --include-lg-model
```

Скрипт создаст директорию `wheels\` со всеми необходимыми пакетами.

### 1.3 Скачивание PostgreSQL

Скачайте installer PostgreSQL 15 для Windows:
- https://www.postgresql.org/download/windows/
- Выберите: `postgresql-15.x-windows-x64.exe`

### 1.4 Что нужно перенести

Создайте архив для переноса, включающий:

```
transfer_package/
├── NER-app/          # Весь каталог проекта
│   └── wheels/       # Скачанные wheels
├── postgresql-15.x-windows-x64.exe  # Установщик PostgreSQL
└── README_TRANSFER.txt
```

Размер архива: ~2-4 GB (зависит от набора пакетов).

---

## Шаг 2: Установка на изолированной машине

### 2.1 Установка PostgreSQL

1. Запустите `postgresql-15.x-windows-x64.exe`
2. Выберите компоненты: PostgreSQL Server, Command Line Tools
3. Запомните пароль пользователя `postgres`
4. Порт: **5432** (по умолчанию)
5. Locale: **Russian, Russia** (если нужна русская локаль БД)
6. Завершите установку

Проверка:
```bat
psql -U postgres -c "SELECT version();"
```

### 2.2 Установка Python (если не установлен)

Скачайте Python 3.11 с https://www.python.org/downloads/windows/  
(нужна offline-версия, если нет интернета)

При установке отметьте:
- ✅ Add Python to PATH
- ✅ Install for all users

### 2.3 Запуск offline установки

```bat
cd C:\NER-app
scripts\install_offline.bat
```

Скрипт выполнит:
1. Создание виртуального окружения `venv\`
2. Установку всех пакетов из `wheels\`
3. Установку spaCy русских моделей
4. Создание необходимых директорий

### 2.4 Инициализация базы данных

```bat
scripts\setup_database.bat
```

При запросе введите пароль `postgres`.

### 2.5 Настройка конфигурации

Отредактируйте `config\label-studio.env`:
```
POSTGRE_PASSWORD=LabelStudio2024!   # Смените на свой пароль
LABEL_STUDIO_HOST=http://localhost:8080
```

Отредактируйте `config\ml-backend.env`:
```
SPACY_MODEL=ru_core_news_sm
MODELS_DIR=C:\NER-app\models
LOGS_DIR=C:\NER-app\logs
```

### 2.6 Запуск

```bat
scripts\start_all.bat
```

---

## Проверка установки

```bat
venv\Scripts\activate
python -c "import spacy; nlp = spacy.load('ru_core_news_sm'); doc = nlp('Москва — столица России'); print([(e.text, e.label_) for e in doc.ents])"
```

Ожидаемый вывод:
```
[('Москва', 'LOC'), ('России', 'LOC')]
```

---

## Обновление wheels

Если нужно обновить пакеты или добавить новые:

1. На машине с интернетом запустите `scripts\download_wheels.bat` заново
2. Скопируйте новые `.whl` файлы в `wheels\`
3. На изолированной машине установите новые пакеты:
   ```bat
   venv\Scripts\activate
   pip install PACKAGE_NAME --no-index --find-links=wheels\
   ```

---

## Возможные проблемы

### "Package not found" при установке

Не хватает wheel-файла. Решение:
1. На машине с интернетом: `pip download PACKAGE --dest wheels\ --platform win_amd64`
2. Перенесите файл в `wheels\`
3. Повторите установку

### PostgreSQL не запускается

Проверьте службу Windows:
```bat
sc query postgresql-x64-15
net start postgresql-x64-15
```

### spaCy модель не найдена

```bat
venv\Scripts\activate
pip install wheels\ru_core_news_sm-3.7.0-py3-none-any.whl
python -m spacy link ru_core_news_sm ru
```
