"""
Все письма сайта в одном месте.

Отправка идёт через почтовый бэкенд из settings.MAILERS
(в разработке — консоль, в бою — SMTP).
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, mailers
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def _absolute(path):
    return settings.SITE_URL.rstrip('/') + path


def _build(subject, text, to_email):
    return EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=None,  # DEFAULT_FROM_EMAIL
        to=[to_email],
    )


def _send(message):
    """Отправить одно письмо. Ошибка почты не должна ронять страницу."""
    try:
        message.send()
        return True
    except Exception:  # noqa: BLE001 — SMTP может упасть как угодно
        logger.exception('Не удалось отправить письмо %s', message.to)
        return False


def send_activation_code(user, code):
    text = (
        f'Здравствуйте, {user.username}!\n\n'
        f'Ваш код подтверждения регистрации на MMORPG Board: {code}\n\n'
        f'Код действует 10 минут. Введите его на странице:\n'
        f'{_absolute(reverse("verify_email"))}\n\n'
        'Если вы не регистрировались, просто проигнорируйте это письмо.'
    )
    return _send(_build('Код подтверждения регистрации', text, user.email))


def send_new_reply_notification(reply):
    """Автору объявления: на его объявление пришёл отклик."""
    post = reply.post
    text = (
        f'Здравствуйте, {post.author.username}!\n\n'
        f'Пользователь {reply.author.username} откликнулся '
        f'на ваше объявление «{post.title}»:\n\n'
        f'{reply.text}\n\n'
        f'Все отклики: {_absolute(reverse("my_replies"))}?post={post.pk}'
    )
    return _send(_build(f'Новый отклик на «{post.title}»', text, post.author.email))


def send_reply_accepted_notification(reply):
    """Автору отклика: его отклик приняли."""
    post = reply.post
    text = (
        f'Здравствуйте, {reply.author.username}!\n\n'
        f'{post.author.username} принял ваш отклик на объявление «{post.title}».\n\n'
        f'Объявление: {_absolute(post.get_absolute_url())}'
    )
    return _send(_build('Ваш отклик принят', text, reply.author.email))


def send_newsletter(newsletter):
    """
    Разослать новость всем подтверждённым пользователям.

    Каждому уходит отдельное письмо (адреса не видны друг другу),
    все письма отправляются через одно соединение с почтовым сервером.
    Возвращает число отправленных писем.
    """
    User = get_user_model()
    emails = (
        User.objects
        .filter(is_active=True, email_verified=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )

    messages = [_build(newsletter.subject, newsletter.body, email) for email in emails]
    sent = mailers.default.send_messages(messages) if messages else 0

    newsletter.sent_at = timezone.now()
    newsletter.recipients_count = sent or 0
    newsletter.save(update_fields=['sent_at', 'recipients_count'])
    return sent or 0
