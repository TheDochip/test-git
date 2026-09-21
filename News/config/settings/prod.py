import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import env_list


DEBUG = False

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('Укажите DJANGO_ALLOWED_HOSTS в .env (например: vibes.ru,www.vibes.ru)')

# Полные адреса с протоколом: https://vibes.ru
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

# Django стоит за nginx/прокси, который терминирует HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# HSTS включайте только когда убедились, что HTTPS работает (например, 31536000).
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0

LOGGING['loggers']['django'] = {  # noqa: F405
    'handlers': ['console'],
    'level': 'WARNING',
}
