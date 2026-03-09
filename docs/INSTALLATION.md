# Инструкция по установке NER-app

## Требования к системе

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| ОС | Windows 10 x64 | Windows 10/11 x64 |
| Python | 3.10 | 3.11 |
| RAM | 4 GB | 8+ GB |
| Disk | 5 GB | 10+ GB |
| CPU | 4 cores | 8+ cores |

## Компоненты

- **PostgreSQL 15+** — база данных для Label Studio
- **Label Studio 1.22.0** — платформа разметки
- **ML Backend** — Flask-сервис с NER на spaCy 3.7.2

---

## Вариант A: Установка с интернетом

### 1. Установка PostgreSQL

1. Скачайте PostgreSQL 15+ с https://www.postgresql.org/download/windows/
2. Запустите установщик, запомните пароль пользователя `postgres`
3. При установке отметьте компонент **pgAdmin 4** (опционально)
4. Убедитесь, что PostgreSQL добавлен в PATH

### 2. Инициализация базы данных

```bat
scripts\setup_database.bat
```

При запросе пароля введите пароль пользователя `postgres`.

### 3. Создание виртуального окружения

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Настройка конфигурации

Отредактируйте файлы:
- `config\label-studio.env` — настройки Label Studio и БД
- `config\ml-backend.env` — настройки ML Backend

**Обязательно смените пароли!**

### 5. Запуск сервисов

```bat
scripts\start_all.bat
```

Или отдельно:
```bat
scripts\start_ml_backend.bat   # В первом окне
scripts\start_label_studio.bat  # Во втором окне
```

---

## Вариант B: Offline установка (изолированная машина)

См. [OFFLINE_SETUP.md](OFFLINE_SETUP.md)

---

## Первоначальная настройка Label Studio

1. Откройте http://localhost:8080
2. Зарегистрируйте аккаунт администратора
3. Создайте новый проект:
   - Название: "NER Разметка"
   - Тип задачи: **Named Entity Recognition**
4. Настройте шаблон разметки (пример):

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

5. Подключите ML Backend:
   - Settings → Machine Learning → Add Model
   - URL: `http://localhost:9090`
   - Название: "spaCy NER Backend"

---

## Проверка работоспособности

### Проверка ML Backend

```bat
curl http://localhost:9090/health
```

Ожидаемый ответ:
```json
{"status": "UP", "model_class": "CombinedNERBackend"}
```

### Проверка Label Studio

Откройте http://localhost:8080 в браузере.

### Проверка подключения к PostgreSQL

```bat
scripts\setup_database.bat
```

---

## Структура директорий

```
NER-app/
├── venv/              # Виртуальное окружение Python
├── logs/              # Лог-файлы
│   ├── app.log
│   ├── predict.log
│   ├── fit.log
│   ├── webapi.log
│   ├── webapi_errors.log
│   └── training.log
├── models/            # Сохранённые модели
│   └── fine_tuned/    # Дообученные модели
│       ├── model_final/
│       └── checkpoint_*/
├── data/              # Данные для разметки
└── wheels/            # Wheel-пакеты для offline установки
```

---

## Смена паролей

1. Измените `POSTGRE_PASSWORD` в `config\label-studio.env`
2. Измените пароль в PostgreSQL:
   ```sql
   ALTER USER label_studio_user WITH PASSWORD 'новый_пароль';
   ```
3. Обновите `config\postgresql-init.sql` для будущих установок
