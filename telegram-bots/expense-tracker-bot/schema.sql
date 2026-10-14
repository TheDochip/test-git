-- Схема БД для бота учёта расходов (PostgreSQL 13+)
-- Применить: psql -d expenses -f schema.sql

CREATE TABLE IF NOT EXISTS users (
    telegram_id   BIGINT PRIMARY KEY,
    username      VARCHAR(64),
    first_name    VARCHAR(128),
    monthly_limit NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (monthly_limit >= 0),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS expenses (
    id           SERIAL PRIMARY KEY,
    telegram_id  BIGINT NOT NULL REFERENCES users (telegram_id) ON DELETE CASCADE,
    amount       NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    category_id  INTEGER REFERENCES categories (id) ON DELETE SET NULL,
    description  TEXT,
    expense_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Почти все запросы бота — «расходы пользователя за период»
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (telegram_id, expense_date);

INSERT INTO categories (name) VALUES
    ('Еда'), ('Транспорт'), ('Жильё'), ('Развлечения'), ('Здоровье'), ('Одежда'), ('Другое')
ON CONFLICT (name) DO NOTHING;
