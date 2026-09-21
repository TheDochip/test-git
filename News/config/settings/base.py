import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent

# .env ищем в корне проекта, а не в текущей рабочей папке.
load_dotenv(BASE_DIR / '.env')


def env_list(name, default=''):
    """Читает из окружения список через запятую: 'a.com, b.com' -> ['a.com', 'b.com']."""
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


SECRET_KEY = os.environ['SECRET_KEY']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'news',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'news.context_processors.navigation',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# База данных общая для dev и prod, параметры берутся из .env.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'news.validators.DigitValidator'},
    {'NAME': 'news.validators.SpecialCharactersValidator'},
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Europe/Amsterdam'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # сюда собирает collectstatic

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'news.User'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'news_list'
LOGOUT_REDIRECT_URL = 'news_list'


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL') or EMAIL_HOST_USER or 'noreply@vibes.local'
EMAIL_TIMEOUT = 10


# ---------------------------------------------------------------
# Настройки приложения news
# ---------------------------------------------------------------

# Коды подтверждения email
ACTIVATION_CODE_TTL_MINUTES = 10
ACTIVATION_CODE_MAX_ATTEMPTS = 5          # неверных вводов на один код
ACTIVATION_CODE_RESEND_COOLDOWN = 60      # секунд между отправками на один адрес
ACTIVATION_CODE_MAX_PER_HOUR = 5          # писем на один адрес в час

# Ограничения на загружаемые файлы, МБ
MAX_IMAGE_SIZE_MB = 5
MAX_VIDEO_SIZE_MB = 100
MAX_FILE_SIZE_MB = 20


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'news': {'handlers': ['console'], 'level': 'INFO'},
    },
}
