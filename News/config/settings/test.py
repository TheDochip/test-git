import os
import tempfile

os.environ.setdefault('SECRET_KEY', 'test-secret-key-not-for-production')

from .base import *  # noqa: E402,F401,F403


DEBUG = False
ALLOWED_HOSTS = ['testserver']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
MEDIA_ROOT = tempfile.mkdtemp(prefix='vibes-test-media-')
