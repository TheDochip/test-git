"""Работа с PostgreSQL. Все запросы параметризованы (%s), соединения — из пула."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Iterator

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from config import DB_CONFIG

_pool = ThreadedConnectionPool(minconn=1, maxconn=5, **DB_CONFIG)


@contextmanager
def cursor(dict_rows: bool = False) -> Iterator:
    """Выдаёт курсор; коммит при успехе, откат при ошибке, соединение возвращается в пул."""
    conn = _pool.getconn()
    try:
        with conn:  # транзакция: commit / rollback
            with conn.cursor(cursor_factory=RealDictCursor if dict_rows else None) as cur:
                yield cur
    finally:
        _pool.putconn(conn)


def register_user(telegram_id: int, username: str, first_name: str) -> None:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE
               SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
            """,
            (telegram_id, username, first_name),
        )


def get_categories() -> list[str]:
    with cursor() as cur:
        cur.execute("SELECT name FROM categories ORDER BY name")
        return [row[0] for row in cur.fetchall()]


def add_expense(telegram_id: int, amount: Decimal, category: str,
                description: str | None, expense_date: date) -> bool:
    """Добавляет расход. Возвращает False, если категории не существует."""
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO expenses (telegram_id, amount, category_id, description, expense_date)
            SELECT %s, %s, c.id, %s, %s FROM categories c WHERE lower(c.name) = lower(%s)
            """,
            (telegram_id, amount, description, expense_date, category),
        )
        return cur.rowcount == 1


def delete_last_expense(telegram_id: int) -> dict | None:
    with cursor(dict_rows=True) as cur:
        cur.execute(
            """
            DELETE FROM expenses
             WHERE id = (SELECT id FROM expenses WHERE telegram_id = %s
                          ORDER BY created_at DESC, id DESC LIMIT 1)
            RETURNING amount, description, expense_date
            """,
            (telegram_id,),
        )
        return cur.fetchone()


def get_expenses(telegram_id: int, start: date, end: date) -> list[dict]:
    with cursor(dict_rows=True) as cur:
        cur.execute(
            """
            SELECT e.amount, e.description, e.expense_date, c.name AS category_name
              FROM expenses e
              LEFT JOIN categories c ON c.id = e.category_id
             WHERE e.telegram_id = %s AND e.expense_date BETWEEN %s AND %s
             ORDER BY e.expense_date DESC, e.id DESC
            """,
            (telegram_id, start, end),
        )
        return cur.fetchall()


def get_totals_by_category(telegram_id: int, start: date, end: date) -> list[dict]:
    with cursor(dict_rows=True) as cur:
        cur.execute(
            """
            SELECT c.name AS category_name, SUM(e.amount) AS total
              FROM expenses e
              LEFT JOIN categories c ON c.id = e.category_id
             WHERE e.telegram_id = %s AND e.expense_date BETWEEN %s AND %s
             GROUP BY c.name
             ORDER BY total DESC
            """,
            (telegram_id, start, end),
        )
        return cur.fetchall()


def get_total(telegram_id: int, start: date, end: date) -> Decimal:
    with cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) FROM expenses
             WHERE telegram_id = %s AND expense_date BETWEEN %s AND %s
            """,
            (telegram_id, start, end),
        )
        return cur.fetchone()[0]


def get_limit(telegram_id: int) -> Decimal:
    with cursor() as cur:
        cur.execute("SELECT monthly_limit FROM users WHERE telegram_id = %s", (telegram_id,))
        row = cur.fetchone()
        return row[0] if row else Decimal(0)


def set_limit(telegram_id: int, limit: Decimal) -> None:
    with cursor() as cur:
        cur.execute("UPDATE users SET monthly_limit = %s WHERE telegram_id = %s", (limit, telegram_id))
