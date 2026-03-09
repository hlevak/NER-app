# Troubleshooting

## Label Studio

### Ошибка: "Cannot connect to database"

**Симптом:** Label Studio не запускается, ошибка подключения к PostgreSQL.

**Решение:**
1. Проверьте, запущен ли PostgreSQL:
   ```bat
   sc query postgresql-x64-15
   ```
2. Запустите сервис при необходимости:
   ```bat
   net start postgresql-x64-15
   ```
3. Проверьте параметры в `config/label-studio.env`:
   - `POSTGRE_HOST` — обычно `localhost`
   - `POSTGRE_PORT` — обычно `5432`
   - `POSTGRE_USER`, `POSTGRE_PASSWORD` — совпадают с инициализацией БД

4. Проверьте подключение вручную:
   ```bat
   psql -U label_studio_user -h localhost -d label_studio
   ```

### Ошибка: "Error loading label_studio"

**Симптом:** `ModuleNotFoundError: No module named 'label_studio'`

**Решение:**
```bat
venv\Scripts\activate
pip install label-studio==1.22.0 --no-index --find-links=wheels\
```

### Label Studio не показывает предсказания ML Backend

**Шаги диагностики:**
1. Проверьте, что ML Backend запущен: `curl http://localhost:9090/health`
2. В Label Studio: Settings → Machine Learning → проверьте статус модели
3. Нажмите "Validate and Save" для принудительной проверки
4. Посмотрите логи ML Backend: `logs/ml-backend.log`

---

## ML Backend

### Ошибка: "OSError: [E050] Can't find model 'ru_core_news_sm'"

**Симптом:** spaCy модель не найдена.

**Решение:**
```bat
venv\Scripts\activate
pip install wheels\ru_core_news_sm-3.7.0-py3-none-any.whl
```

Или проверьте установленные модели:
```bat
python -m spacy info
```

### Ошибка при импорте ml_backend

**Симптом:** `ImportError` при запуске `python -m ml_backend.wsgi`

**Решение:**
1. Убедитесь, что вы запускаете из корня проекта (`C:\NER-app\`)
2. Активируйте виртуальное окружение: `venv\Scripts\activate`
3. Проверьте установку: `pip list | findstr spacy`

### ML Backend запускается, но predict возвращает пустой результат

**Проверьте:**
1. Тип разметки в Label Studio — должен быть `labels` (не `taxonomy` и не `choices`)
2. Структуру label config — должен присутствовать тег `<Labels name="label" toName="text">`
3. Логи: `logs/predict.log`

### Дообучение зависает или завершается с ошибкой

**Проверьте:**
1. `logs/training.log` — подробности ошибки
2. `logs/fit.log` — количество примеров
3. Убедитесь, что в данных есть хотя бы несколько примеров с каждым типом сущности
4. Попробуйте уменьшить `TRAINING_ITERATIONS=10` для теста

---

## PostgreSQL

### Ошибка при инициализации БД: "ERROR: database 'label_studio' already exists"

Это нормально — скрипт проверяет существование БД.

### Ошибка аутентификации PostgreSQL

**Симптом:** `FATAL: password authentication failed for user "label_studio_user"`

**Решение:**
1. Подключитесь как администратор:
   ```bat
   psql -U postgres
   ```
2. Измените пароль:
   ```sql
   ALTER USER label_studio_user WITH PASSWORD 'LabelStudio2024!';
   ```
3. Убедитесь, что пароль совпадает в `config/label-studio.env`

### PostgreSQL принимает только md5 аутентификацию

**Симптом:** `SCRAM authentication requires libpq version 10 or above`

**Решение** — в `pg_hba.conf` (обычно `C:\Program Files\PostgreSQL\15\data\pg_hba.conf`):
```
# Замените scram-sha-256 на md5
host    all             all             127.0.0.1/32            md5
```

Перезапустите службу: `net stop postgresql-x64-15 && net start postgresql-x64-15`

---

## Offline установка

### "Package not found in local repository"

**Симптом:** `pip install ... --no-index` не находит пакет.

**Решение:**
1. Проверьте наличие файла в `wheels\`:
   ```bat
   dir wheels\ | findstr PACKAGE_NAME
   ```
2. На машине с интернетом скачайте недостающий пакет:
   ```bat
   pip download PACKAGE_NAME --dest wheels\ --platform win_amd64 --python-version 311 --implementation cp --only-binary=:all:
   ```
3. Перенесите файл

### Ошибка: binary wheel несовместим

**Симптом:** `ERROR: ... is not a supported wheel on this platform`

**Причина:** Wheel скачан для другой версии Python или архитектуры.

**Решение:** Скачайте правильный wheel:
```bat
pip download PACKAGE --dest wheels\ --platform win_amd64 --python-version 311
```

---

## Производительность

### ML Backend медленно отвечает

1. Используйте `ru_core_news_sm` вместо `ru_core_news_lg` (быстрее в 3-5x)
2. Уменьшите размер батча в Label Studio (Settings → Machine Learning → batch size)
3. Отключите WebAPI если он медленный: очистите `WEBAPI_BASE_URL` в конфиге

### Большой размер логов

Логи ротируются автоматически (10 MB × 5 файлов = 50 MB max).

Для более агрессивной ротации в `config/ml-backend.env`:
```
LOG_MAX_BYTES=1048576   # 1 MB
LOG_BACKUP_COUNT=3
```

### Высокое потребление RAM

- `ru_core_news_sm`: ~300 MB RAM
- `ru_core_news_lg`: ~700 MB RAM

Для снижения потребления используйте `ru_core_news_sm`.

---

## Диагностические команды

```bat
REM Проверка версий
venv\Scripts\activate
python -m spacy info
python -c "import label_studio_ml; print(label_studio_ml.__version__)"
python -c "import flask; print(flask.__version__)"
psql --version

REM Тест ML Backend напрямую
curl -X POST http://localhost:9090/predict -H "Content-Type: application/json" -d "{\"tasks\":[{\"data\":{\"text\":\"Тест\"}}]}"

REM Просмотр последних логов
type logs\app_errors.log
type logs\ml-backend.log
```
