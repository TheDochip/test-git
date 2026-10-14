# 💱 Currency Converter Bot

Telegram-бот, который переводит сумму из одной валюты в другую по актуальному курсу.

```
доллар рубль 100
→ 100,00 USD (доллар США) = 8 150,00 RUB (российский рубль)
  Курс: 1 USD = 81.5000 RUB          (курс в примере условный)
```

## Возможности
- 24 валюты; можно писать ISO-код (`USD`) или слово (`доллар`), регистр не важен
- Дробные суммы через точку или запятую
- Понятные сообщения об ошибках ввода: неизвестная валюта, не число, одинаковые валюты
- Курсы из открытого API [open.er-api.com](https://www.exchangerate-api.com/docs/free) (без ключа), кеш на 10 минут, таймаут запросов
- Команды: `/start`, `/help`, `/values`

## Стек
Python 3.10+, pyTelegramBotAPI, requests, python-dotenv, unittest

## Архитектура
| Файл | Назначение |
|---|---|
| `bot.py` | обработчики Telegram, только ввод/вывод |
| `converter.py` | разбор запроса, получение курса (`RateProvider` с кешем), форматирование |
| `currencies.py` | справочник валют и синонимов |
| `tests/` | 14 юнит-тестов; HTTP подменяется фейком, сеть не нужна |

Логика отделена от Telegram, поэтому `RateProvider` получает HTTP-клиент и часы через конструктор (dependency injection) — так тестируются кеш и обработка сетевых ошибок.

## Запуск
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # вставьте BOT_TOKEN от @BotFather
python bot.py
```

## Тесты
```bash
python -m unittest discover -s tests     # или: pytest
```
