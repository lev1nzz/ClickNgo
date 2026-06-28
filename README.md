# URL Shortener Service

Тестовое задание ООО «КЕХ ЕКОММЕРЦ» - Авито: Сервис сокращения URL-адресов на FastAPI.

Ссылка на задание:
https://github.com/avito-tech/auto-backend-trainee-assignment

## Запуск

Установка зависимостей:
```
pip install -r requirements.txt
```

Запуск сервера:
```
uvicorn main:app --reload
```

Сервер будет доступен по адресу: http://localhost:8000

## API

### Создание короткой ссылки

```
POST /short_url
Body: {"original_url": "https://example.com/long/url"}
Response: {"original_url": "...", "short_slug": "abc123"}
```

### Переход по короткой ссылке

```
GET /{short_slug}
```

Происходит редирект (301) на оригинальный URL.

## База данных

Используется SQLite. Таблица `url_db.db` создается автоматически при запуске.

Структура таблицы:
- id - первичный ключ
- original_url - длинная ссылка
- short_slug - короткий идентификатор (уникальный)

## Структура проекта

```
src/
├── database/
│   ├── db.py       # Настройка подключения к БД
│   └── models.py   # Модель URL
├── schemas.py      # Pydantic схемы
├── config.py       # Константы и переменные окружения
├── shortener.py    # Логика сокращения ссылок
└── service.py      # Бизнес-логика
main.py             # Точка входа
```

## Используемые технологии
- Python 3.12
- FastAPI 0.135.3
- SQLAlchemy 2.0.49
- SQLite
- Pydantic 2.13.0