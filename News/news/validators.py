import os

import bleach
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


# ---------------------------------------------------------------
# Пароли
# ---------------------------------------------------------------

class DigitValidator:
    def validate(self, password, user=None):
        if not any(char.isdigit() for char in password):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру.', code='password_no_digit')

    def get_help_text(self):
        return 'Пароль должен содержать хотя бы одну цифру.'


class SpecialCharactersValidator:
    SPECIAL_CHARACTERS = '!@#$%^&*()-_=+[]{};:,.?'

    def validate(self, password, user=None):
        if not any(char in self.SPECIAL_CHARACTERS for char in password):
            raise ValidationError(
                f'Пароль должен содержать хотя бы один спецсимвол: {self.SPECIAL_CHARACTERS}',
                code='password_no_special',
            )

    def get_help_text(self):
        return f'Пароль должен содержать хотя бы один спецсимвол: {self.SPECIAL_CHARACTERS}'


# ---------------------------------------------------------------
# Rich text
# ---------------------------------------------------------------

ALLOWED_RICH_TEXT_TAGS = [
    'p', 'br', 'div', 'strong', 'b', 'em', 'i', 'u',
    'h2', 'h3', 'ul', 'ol', 'li', 'blockquote', 'a',
]

ALLOWED_RICH_TEXT_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
}


def _force_safe_link_rel(attrs, new=False):
    """Все ссылки из текста открываются в новой вкладке без доступа к window.opener."""
    href_key = (None, 'href')
    if href_key in attrs:
        attrs[(None, 'target')] = '_blank'
        attrs[(None, 'rel')] = 'noopener noreferrer nofollow'
    return attrs


def clean_rich_text(value):
    cleaned = bleach.clean(
        value or '',
        tags=ALLOWED_RICH_TEXT_TAGS,
        attributes=ALLOWED_RICH_TEXT_ATTRIBUTES,
        protocols=['http', 'https', 'mailto'],
        strip=True,
    )
    return bleach.linkify(cleaned, callbacks=[_force_safe_link_rel], parse_email=False)


# ---------------------------------------------------------------
# Ссылки
# ---------------------------------------------------------------

_http_url_validator = URLValidator(schemes=['http', 'https'])


def validate_http_url(value):
    """Разрешаем только http(s): javascript:, data: и прочие схемы отбрасываются."""
    try:
        _http_url_validator(value)
    except ValidationError:
        raise ValidationError('Введите корректную ссылку, начинающуюся с http:// или https://')


def is_http_url(value):
    try:
        validate_http_url(value)
    except ValidationError:
        return False
    return True


# ---------------------------------------------------------------
# Файлы
# ---------------------------------------------------------------

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
VIDEO_EXTENSIONS = ['mp4', 'webm', 'ogg', 'mov']
DOCUMENT_EXTENSIONS = [
    'pdf', 'txt', 'csv', 'rtf',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
    'zip', 'rar', '7z',
]


def get_extension(file):
    return os.path.splitext(file.name)[1].lower().lstrip('.')


def _validate_extension(file, allowed, what):
    extension = get_extension(file)
    if extension not in allowed:
        raise ValidationError(
            f'Недопустимый формат {what}: .{extension or "?"}. Разрешены: {", ".join(allowed)}.'
        )


def _validate_size(file, max_mb):
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f'Файл «{file.name}» больше {max_mb} МБ.')


def validate_image_upload(file):
    _validate_extension(file, IMAGE_EXTENSIONS, 'изображения')
    _validate_size(file, settings.MAX_IMAGE_SIZE_MB)

    # Проверяем, что внутри действительно картинка, а не переименованный файл.
    from PIL import Image

    try:
        position = file.tell()
        Image.open(file).verify()
        file.seek(position)
    except Exception:
        raise ValidationError(f'Файл «{file.name}» не является изображением.')


def validate_video_upload(file):
    _validate_extension(file, VIDEO_EXTENSIONS, 'видео')
    _validate_size(file, settings.MAX_VIDEO_SIZE_MB)


def validate_document_upload(file):
    _validate_extension(file, DOCUMENT_EXTENSIONS, 'файла')
    _validate_size(file, settings.MAX_FILE_SIZE_MB)
