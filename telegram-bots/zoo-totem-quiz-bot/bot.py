"""Telegram-бот «Какое у вас тотемное животное?» для Московского зоопарка.

Пользователь отвечает на 8 вопросов, бот подбирает животное из коллекции зоопарка
и рассказывает о программе опеки. Кнопки — inline, состояние хранится по user_id.
"""
import html
import logging
import os
from urllib.parse import quote

import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from quiz import QuizSession, format_result, progress_bar, validate_data
from quiz_data import ANIMALS

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("zoo-quiz-bot")

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Не задан BOT_TOKEN в .env")
GUARDIANSHIP_URL = os.getenv("GUARDIANSHIP_URL", "https://moscowzoo.ru/")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

validate_data()
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
sessions: dict[int, QuizSession] = {}


def start_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎮 Начать викторину", callback_data="start"))
    return markup


def question_keyboard(session: QuizSession) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    for i, answer in enumerate(session.question["answers"]):
        markup.add(InlineKeyboardButton(answer["text"], callback_data=f"a:{session.current}:{i}"))
    markup.add(InlineKeyboardButton("❌ Отменить", callback_data="cancel"))
    return markup


def result_keyboard(animal_name: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("💝 Узнать про опеку", url=GUARDIANSHIP_URL))
    if BOT_USERNAME:
        share_text = f"Моё тотемное животное — {animal_name}! А какое у тебя?"
        markup.add(InlineKeyboardButton(
            "📣 Поделиться результатом",
            url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}&text={quote(share_text)}",
        ))
    markup.add(InlineKeyboardButton("🔄 Пройти ещё раз", callback_data="start"))
    return markup


def question_text(session: QuizSession) -> str:
    total = len(session.questions)
    return (
        f"<code>{progress_bar(session.current + 1, total)}</code>\n\n"
        f"<b>Вопрос {session.current + 1}/{total}</b>\n\n{session.question['text']}"
    )


@bot.message_handler(commands=["start", "help"])
def cmd_start(message: telebot.types.Message) -> None:
    bot.send_message(
        message.chat.id,
        "Привет! Это викторина <b>«Какое у вас тотемное животное?»</b> 🐾\n\n"
        f"Ответьте на 8 вопросов — и мы подберём вам одного из {len(ANIMALS)} обитателей "
        "Московского зоопарка, расскажем о нём и о том, как взять его под опеку.",
        reply_markup=start_keyboard(),
    )


@bot.message_handler(commands=["quiz"])
def cmd_quiz(message: telebot.types.Message) -> None:
    session = sessions[message.from_user.id] = QuizSession()
    bot.send_message(message.chat.id, question_text(session), reply_markup=question_keyboard(session))


@bot.callback_query_handler(func=lambda call: call.data == "start")
def on_start(call: telebot.types.CallbackQuery) -> None:
    session = sessions[call.from_user.id] = QuizSession()
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, question_text(session), reply_markup=question_keyboard(session))


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def on_cancel(call: telebot.types.CallbackQuery) -> None:
    sessions.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id, "Викторина отменена")
    bot.edit_message_text(
        "Викторина отменена. Вернуться можно в любой момент 👇",
        call.message.chat.id, call.message.message_id, reply_markup=start_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("a:"))
def on_answer(call: telebot.types.CallbackQuery) -> None:
    session = sessions.get(call.from_user.id)
    _, question_index, answer_index = call.data.split(":")
    # Защита от нажатий на кнопки старых сообщений
    if session is None or session.finished or int(question_index) != session.current:
        bot.answer_callback_query(call.id, "Этот вопрос уже неактуален. Нажмите /quiz")
        return

    session.answer(int(answer_index))
    bot.answer_callback_query(call.id)
    chat_id, message_id = call.message.chat.id, call.message.message_id

    if not session.finished:
        bot.edit_message_text(question_text(session), chat_id, message_id,
                              reply_markup=question_keyboard(session))
        return

    result = session.result()
    sessions.pop(call.from_user.id, None)
    username = html.escape(call.from_user.first_name or "Друг")
    animal = ANIMALS[result.winner]
    log.info("user=%s result=%s", call.from_user.id, result.winner)
    bot.edit_message_text(format_result(result, username), chat_id, message_id,
                          reply_markup=result_keyboard(animal["name"]))


@bot.message_handler(func=lambda message: True)
def fallback(message: telebot.types.Message) -> None:
    bot.send_message(message.chat.id, "Пользуйтесь кнопками или командой /quiz 🙂",
                     reply_markup=start_keyboard())


if __name__ == "__main__":
    log.info("Бот запущен")
    bot.infinity_polling(skip_pending=True)
