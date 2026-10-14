"""Telegram-бот для учёта личных расходов с месячным лимитом. Хранение — PostgreSQL."""
import logging
from datetime import date

import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

import db
from config import BOT_TOKEN
from logic import InputError, format_report, limit_status, money, parse_add, parse_limit, period

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("expense-bot")

bot = telebot.TeleBot(BOT_TOKEN)

BUTTONS = {
    "➕ Добавить": "add_help",
    "📅 Сегодня": "today",
    "🗓 Неделя": "week",
    "📆 Месяц": "month",
    "🎯 Лимит": "limit",
    "↩️ Отменить последний": "undo",
}


def main_keyboard() -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(*(KeyboardButton(text) for text in BUTTONS))
    return markup


def add_help_text() -> str:
    return (
        "Чтобы добавить расход:\n"
        "/add <сумма> <категория> [описание]\n\n"
        "Примеры:\n/add 500 Еда Обед\n/add 120,50 Транспорт Метро\n\n"
        "Категории: " + ", ".join(db.get_categories())
    )


@bot.message_handler(commands=["start", "help"])
def cmd_start(message: telebot.types.Message) -> None:
    user = message.from_user
    db.register_user(user.id, user.username or "", user.first_name or "")
    bot.send_message(
        message.chat.id,
        f"Привет, {user.first_name or 'друг'}! 👋 Я помогу вести учёт расходов.\n\n"
        "/add — добавить трату\n/today, /week, /month — отчёты\n"
        "/limit <сумма> — месячный лимит\n/undo — удалить последнюю запись\n\n" + add_help_text(),
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["add"])
def cmd_add(message: telebot.types.Message) -> None:
    user_id = message.from_user.id
    try:
        expense = parse_add(message.text)
    except InputError as error:
        bot.reply_to(message, f"⚠️ {error}")
        return

    db.register_user(user_id, message.from_user.username or "", message.from_user.first_name or "")
    today = date.today()
    if not db.add_expense(user_id, expense.amount, expense.category, expense.description, today):
        bot.reply_to(message, f"Категории «{expense.category}» нет.\n\n" + add_help_text())
        return

    text = f"✅ Записал: {money(expense.amount)} · {expense.category}"
    if expense.description:
        text += f" — {expense.description}"
    start, end, _ = period("month", today)
    status = limit_status(db.get_total(user_id, start, end), db.get_limit(user_id))
    bot.send_message(message.chat.id, f"{text}\n{status}".strip())


def send_report(message: telebot.types.Message, period_name: str) -> None:
    user_id = message.from_user.id
    start, end, title = period(period_name, date.today())
    total = db.get_total(user_id, start, end)
    text = format_report(title, db.get_expenses(user_id, start, end), total,
                         db.get_totals_by_category(user_id, start, end))
    if period_name == "month":
        text += "\n" + limit_status(total, db.get_limit(user_id))
    bot.send_message(message.chat.id, text.strip())


@bot.message_handler(commands=["today", "week", "month"])
def cmd_report(message: telebot.types.Message) -> None:
    send_report(message, message.text.split()[0].lstrip("/").split("@")[0])


@bot.message_handler(commands=["limit"])
def cmd_limit(message: telebot.types.Message) -> None:
    user_id = message.from_user.id
    try:
        new_limit = parse_limit(message.text)
    except InputError as error:
        bot.reply_to(message, f"⚠️ {error}")
        return

    db.register_user(user_id, message.from_user.username or "", message.from_user.first_name or "")
    if new_limit is None:
        current = db.get_limit(user_id)
        bot.send_message(message.chat.id, f"Месячный лимит: {money(current)}" if current > 0
                         else "Лимит не задан. Установить: /limit 30000")
        return
    db.set_limit(user_id, new_limit)
    bot.send_message(message.chat.id, f"🎯 Лимит установлен: {money(new_limit)}" if new_limit > 0
                     else "Лимит снят.")


@bot.message_handler(commands=["undo"])
def cmd_undo(message: telebot.types.Message) -> None:
    deleted = db.delete_last_expense(message.from_user.id)
    if deleted is None:
        bot.send_message(message.chat.id, "Удалять нечего — записей нет.")
    else:
        bot.send_message(message.chat.id, f"↩️ Удалил запись от {deleted['expense_date']:%d.%m}: "
                                          f"{money(deleted['amount'])}")


@bot.message_handler(func=lambda message: True)
def on_button(message: telebot.types.Message) -> None:
    action = BUTTONS.get(message.text)
    if action == "add_help":
        bot.send_message(message.chat.id, add_help_text())
    elif action in ("today", "week", "month"):
        send_report(message, action)
    elif action == "limit":
        message.text = "/limit"
        cmd_limit(message)
    elif action == "undo":
        cmd_undo(message)
    else:
        bot.send_message(message.chat.id, "Не понял 🙂 Используйте кнопки или /help",
                         reply_markup=main_keyboard())


if __name__ == "__main__":
    log.info("Бот запущен")
    bot.infinity_polling(skip_pending=True)
