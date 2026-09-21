"""Отправка и проверка кодов подтверждения email."""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from .models import ActivationCode


logger = logging.getLogger(__name__)


class ActivationError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


def generate_code():
    return f'{secrets.randbelow(10 ** 6):06d}'


def send_activation_code(email):
    """
    Создаёт новый код и отправляет его на email.
    Ограничения: не чаще раза в ACTIVATION_CODE_RESEND_COOLDOWN секунд
    и не больше ACTIVATION_CODE_MAX_PER_HOUR писем в час на один адрес.
    """
    now = timezone.now()
    last_hour = ActivationCode.objects.filter(email__iexact=email, created_at__gte=now - timedelta(hours=1))

    if last_hour.count() >= settings.ACTIVATION_CODE_MAX_PER_HOUR:
        raise ActivationError('Слишком много запросов кода на этот адрес. Попробуйте через час.')

    last_code = last_hour.order_by('-created_at').first()
    if last_code:
        seconds_passed = (now - last_code.created_at).total_seconds()
        wait = int(settings.ACTIVATION_CODE_RESEND_COOLDOWN - seconds_passed)
        if wait > 0:
            raise ActivationError(f'Новый код можно запросить через {wait} сек.')

    # Старые коды больше не действуют.
    ActivationCode.objects.filter(email__iexact=email, is_used=False).update(is_used=True)

    code = generate_code()
    activation = ActivationCode.objects.create(
        email=email,
        code=code,
        expires_at=now + timedelta(minutes=settings.ACTIVATION_CODE_TTL_MINUTES),
    )

    try:
        send_mail(
            'Код подтверждения Vibes',
            f'Ваш код подтверждения: {code}\n\n'
            f'Код действует {settings.ACTIVATION_CODE_TTL_MINUTES} минут. '
            f'Если вы не регистрировались на Vibes, просто проигнорируйте это письмо.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
    except Exception:
        logger.exception('Не удалось отправить код подтверждения на %s', email)
        activation.is_used = True
        activation.save(update_fields=['is_used'])
        raise ActivationError('Не удалось отправить письмо. Проверьте адрес или попробуйте позже.')


def check_activation_code(email, code):
    """Проверяет код. При успехе помечает его использованным, иначе бросает ActivationError."""
    activation = (
        ActivationCode.objects
        .filter(email__iexact=email, is_used=False)
        .order_by('-created_at')
        .first()
    )

    if activation is None:
        raise ActivationError('Неверный код. Запросите новый, если письмо не пришло.')

    if activation.is_expired:
        raise ActivationError('Код просрочен. Запросите новый.')

    if activation.attempts_exhausted:
        raise ActivationError('Слишком много неверных попыток. Запросите новый код.')

    if not constant_time_compare(activation.code, code):
        ActivationCode.objects.filter(pk=activation.pk).update(attempts=F('attempts') + 1)
        raise ActivationError('Неверный код.')

    activation.is_used = True
    activation.save(update_fields=['is_used'])
