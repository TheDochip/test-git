# 💰 Expense Tracker Bot

Telegram-бот для учёта личных расходов с категориями, отчётами и месячным лимитом.
Данные хранятся в PostgreSQL.

## Возможности
- `/add 500 Еда Обед` — добавить трату (категория без учёта регистра, сумма с копейками)
- `/today`, `/week`, `/month` — отчёт за период с разбивкой по категориям и долями
- `/limit 30000` — месячный лимит; после каждой траты бот показывает остаток или превышение
- `/undo` — удалить последнюю запись
- Reply-клавиатура с быстрыми кнопками

## Стек
Python 3.10+, pyTelegramBotAPI, PostgreSQL 16, psycopg2, Docker Compose, unittest

## Устройство БД
`users` — пользователь и лимит, `categories` — справочник, `expenses` — траты
(внешние ключи, `CHECK`-ограничения, индекс по `(telegram_id, expense_date)`).
Схема — в `schema.sql`, она идемпотентна (можно применять повторно).

## Архитектура
| Файл | Назначение |
|---|---|
| `bot.py` | обработчики Telegram |
| `db.py` | SQL-запросы; пул соединений, транзакции через контекстный менеджер, только параметризованные запросы |
| `logic.py` | разбор команд, периоды, форматирование отчётов (без БД — легко тестировать) |
| `config.py` | настройки из `.env` |
| `tests/` | 12 юнит-тестов логики |

## Запуск
```bash
cp .env.example .env          # BOT_TOKEN и DB_PASSWORD
docker compose up -d          # PostgreSQL + автоматическое применение schema.sql
pip install -r requirements.txt
python bot.py
```
Без Docker: создайте БД `expenses` и выполните `psql -d expenses -f schema.sql`.

## Тесты
```bash
python -m unittest discover -s tests
```
