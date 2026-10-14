"""Telegram-бот конвертер валют.

Запуск: заполните .env (см. .env.example) и выполните `python bot.py`.
"""
import logging
import os

import telebot
from dotenv import load_dotenv

from converter import ConversionError, RateProvider, format_result, parse_request
from currencies import currencies_help

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("currency-bot")

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Не задан BOT_TOKEN в .env")

bot = telebot.TeleBot(TOKEN)
rates = RateProvider()

HELP_TEXT = (
    "Я перевожу одну валюту в другую по актуальному курсу.\n\n"
    "Формат: <валюта> <в какую валюту> <количество>\n"
    "Примеры:\n"
    "  доллар рубль 100\n"
    "  EUR USD 25,5\n\n"
    "Список валют: /values"
)


@bot.message_handler(commands=["start", "help"])
def send_help(message: telebot.types.Message) -> None:
    bot.reply_to(message, HELP_TEXT)


@bot.message_handler(commands=["values"])
def send_values(message: telebot.types.Message) -> None:
    bot.reply_to(message, currencies_help())


@bot.message_handler(content_types=["text"])
def convert(message: telebot.types.Message) -> None:
    try:
        result = rates.convert(parse_request(message.text))
    except ConversionError as error:
        bot.reply_to(message, f"⚠️ {error}")
    except Exception:  # непредвиденная ошибка — логируем, пользователю короткий ответ
        log.exception("Ошибка при обработке %r", message.text)
        bot.reply_to(message, "Что-то пошло не так, попробуйте ещё раз.")
    else:
        bot.send_message(message.chat.id, format_result(result))


if __name__ == "__main__":
    log.info("Бот запущен")
    bot.infinity_polling(skip_pending=True)
