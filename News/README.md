# Vibes

Новостной сайт на Django: публикации из блоков (текст, изображения, видео, файлы, ссылки, цитаты),
категории, реакции, комментарии, подписки, регистрация с подтверждением email.

## Запуск локально

```bash
python -m venv venv
venv\Scripts\activate            # Windows (на Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt

copy .env.example .env           # заполните SECRET_KEY и параметры Postgres
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`SECRET_KEY` можно сгенерировать так:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Если `EMAIL_HOST_USER` не заполнен, письма (коды подтверждения, сброс пароля) печатаются в консоль `runserver`.

## Тесты

Быстро, на SQLite, без Postgres и `.env`:

```bash
python manage.py test --settings=config.settings.test
```

## Настройки

| Модуль | Для чего |
|---|---|
| `config.settings.dev` | разработка, используется `manage.py` по умолчанию |
| `config.settings.prod` | продакшен, используется `wsgi.py`/`asgi.py`; нужны `DJANGO_ALLOWED_HOSTS` и HTTPS |
| `config.settings.test` | тесты на SQLite |

## Структура приложения `news`

| Файл | Что внутри |
|---|---|
| `models.py` | модели |
| `views.py` | представления |
| `forms.py` | формы |
| `blocks.py` | разбор, проверка и сохранение блоков из конструктора публикаций |
| `activation.py` | отправка и проверка кодов подтверждения email |
| `validators.py` | валидаторы паролей, очистка HTML, проверка ссылок и загружаемых файлов |
