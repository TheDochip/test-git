"""Настройки читаются из переменных окружения / файла .env (см. .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN в .env")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "expenses"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}
