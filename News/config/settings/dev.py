from .base import *  # noqa: F401,F403


DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Если почта не настроена, письма (коды подтверждения, сброс пароля)
# печатаются в консоль runserver, и регистрацию можно проверить без SMTP.
if not EMAIL_HOST_USER:  # noqa: F405
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
