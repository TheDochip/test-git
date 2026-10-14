"""Чистая логика бота: разбор команд, периоды, форматирование. Без БД и Telegram."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

MAX_AMOUNT = Decimal("10000000")


class InputError(Exception):
    """Ошибка ввода, текст которой можно показать пользователю."""


@dataclass(frozen=True)
class NewExpense:
    amount: Decimal
    category: str
    description: str | None


def parse_amount(raw: str) -> Decimal:
    try:
        amount = Decimal(raw.replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise InputError(f"«{raw}» — не число. Пример: 450 или 99,90") from None
    if not amount.is_finite() or amount <= 0:
        raise InputError("Сумма должна быть больше нуля.")
    if amount > MAX_AMOUNT:
        raise InputError("Слишком большая сумма — проверьте, нет ли лишних нулей.")
    return amount


def parse_add(text: str) -> NewExpense:
    """«/add 500 еда обед в кафе» -> NewExpense(500.00, 'Еда', 'обед в кафе')"""
    parts = text.split(maxsplit=3)
    if len(parts) < 3:
        raise InputError(
            "Формат: /add <сумма> <категория> [описание]\n"
            "Пример: /add 500 Еда Обед"
        )
    _, amount_raw, category_raw, *rest = parts
    description = rest[0].strip() if rest else None
    return NewExpense(parse_amount(amount_raw), category_raw.capitalize(), description or None)


def parse_limit(text: str) -> Decimal | None:
    """«/limit» -> None (показать текущий), «/limit 30000» -> Decimal, «/limit 0» -> снять лимит."""
    parts = text.split()
    if len(parts) == 1:
        return None
    try:
        value = Decimal(parts[1].replace(",", "."))
    except InvalidOperation:
        raise InputError("Формат: /limit <сумма>. Чтобы снять лимит: /limit 0") from None
    if not value.is_finite() or value < 0:
        raise InputError("Лимит не может быть отрицательным.")
    return value.quantize(Decimal("0.01"))


def period(name: str, today: date) -> tuple[date, date, str]:
    """Границы периода (включительно) и подпись для пользователя."""
    if name == "today":
        return today, today, "сегодня"
    if name == "week":
        return today - timedelta(days=6), today, "последние 7 дней"
    if name == "month":
        return today.replace(day=1), today, "текущий месяц"
    raise ValueError(name)


def money(value: Decimal | float | int) -> str:
    """Decimal('12345.5') -> «12 345,50 ₽»"""
    return f"{Decimal(value):,.2f}".replace(",", " ").replace(".", ",") + " ₽"


def limit_status(spent: Decimal, limit: Decimal) -> str:
    if limit <= 0:
        return ""
    if spent > limit:
        return f"⚠️ Лимит {money(limit)} превышен на {money(spent - limit)}"
    percent = int(spent / limit * 100)
    return f"Лимит: {money(limit)} · использовано {percent}% · осталось {money(limit - spent)}"


def format_report(title: str, rows: list[dict], total: Decimal, by_category: list[dict]) -> str:
    if not rows:
        return f"За {title} расходов нет 🎉"
    lines = [f"📊 Расходы за {title}:", ""]
    for row in rows:
        line = f"{row['expense_date']:%d.%m} · {money(row['amount'])} · {row['category_name'] or 'Без категории'}"
        if row.get("description"):
            line += f" — {row['description']}"
        lines.append(line)
    if len(by_category) > 1:
        lines += ["", "По категориям:"]
        for item in by_category:
            share = int(item["total"] / total * 100) if total else 0
            lines.append(f"  {item['category_name'] or 'Без категории'}: {money(item['total'])} ({share}%)")
    lines += ["", f"💰 Итого: {money(total)}"]
    return "\n".join(lines)
