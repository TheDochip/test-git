from datetime import timedelta

from django import template
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.template.defaultfilters import date as date_filter
from django.utils import timezone

from news.validators import is_http_url


register = template.Library()


@register.filter
def http_url(value):
    """
    Отдаёт ссылку, только если она http(s). Защищает старые записи,
    сохранённые до валидации, от ссылок вида javascript:...
    """
    return value if value and is_http_url(value) else ''


@register.filter
def smart_date(value):
    """«5 минут назад» для свежего, «18 сентября» в этом году, «18 сентября 2025» для старого."""
    if not value:
        return ''
    now = timezone.now()
    if now - value < timedelta(hours=24):
        return naturaltime(value)
    local = timezone.localtime(value)
    if local.year == timezone.localtime(now).year:
        return date_filter(local, 'j E')
    return date_filter(local, 'j E Y')


@register.filter
def link_domain(value):
    """https://www.example.com/page -> example.com"""
    from urllib.parse import urlparse

    host = urlparse(value or '').netloc
    return host[4:] if host.startswith('www.') else host


@register.filter
def filename(value):
    """post_files/report.pdf -> report.pdf"""
    return str(value or '').rsplit('/', 1)[-1]


@register.simple_tag(takes_context=True)
def query_with(context, **kwargs):
    """Текущие GET-параметры с заменой: {% query_with category=5 page=None %} -> ?q=x&category=5"""
    params = context['request'].GET.copy()
    for key, value in kwargs.items():
        params.pop(key, None)
        if value not in (None, ''):
            params[key] = value
    encoded = params.urlencode()
    return f'?{encoded}' if encoded else '?'
