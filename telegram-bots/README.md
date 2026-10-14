# Telegram-боты на Python

Три пет-проекта на pyTelegramBotAPI. В каждом бизнес-логика отделена от Telegram и покрыта тестами.

| Проект | Что делает | Ключевое |
|---|---|---|
| [currency-converter-bot](currency-converter-bot) | Конвертер валют по актуальному курсу | REST API, кеширование, обработка ошибок, DI для тестов |
| [zoo-totem-quiz-bot](zoo-totem-quiz-bot) | Викторина «Тотемное животное» для Московского зоопарка | inline-кнопки, состояние пользователя, балансировка перебором |
| [expense-tracker-bot](expense-tracker-bot) | Учёт расходов с лимитом | PostgreSQL, SQL с агрегатами, пул соединений, Docker Compose |

Запуск тестов во всех проектах: `python -m unittest discover -s tests` из папки проекта.
