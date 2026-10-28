"""
Очистка HTML объявлений.

Текст объявления приходит из визуального редактора в виде HTML, поэтому его
нельзя выводить как есть: пользователь может вставить <script>, onerror=...,
javascript:-ссылку и т. п. Здесь HTML разбирается стандартным html.parser и
собирается заново только из разрешённых тегов и атрибутов (whitelist):

* всё, что не разрешено, выбрасывается (текст внутри обычных тегов остаётся,
  содержимое <script>, <style> и подобных удаляется целиком);
* ссылки и картинки — только http(s), mailto (для ссылок) и локальные /media/;
* <iframe> — только с видеохостингов из VIDEO_EMBED_PREFIXES.

Внешних зависимостей нет.
"""

from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

ALLOWED_TAGS = {
    'p', 'br', 'hr', 'div', 'span',
    'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'sub', 'sup',
    'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'blockquote', 'pre', 'code',
    'a', 'img', 'iframe',
    'figure', 'figcaption',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
}

VOID_TAGS = {'br', 'hr', 'img'}

# Теги, содержимое которых удаляется вместе с ними
DROP_CONTENT_TAGS = {
    'script', 'style', 'noscript', 'template', 'textarea',
    'title', 'head', 'object', 'embed', 'svg', 'math',
}

ALLOWED_ATTRS = {
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt', 'title', 'width', 'height'},
    'iframe': {'src', 'width', 'height', 'title', 'allowfullscreen'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan'},
    'ol': {'start'},
}

# Разрешённые источники встроенного видео
VIDEO_EMBED_PREFIXES = (
    'https://www.youtube.com/embed/',
    'https://youtube.com/embed/',
    'https://www.youtube-nocookie.com/embed/',
    'https://player.vimeo.com/video/',
    'https://rutube.ru/play/embed/',
    'https://vk.com/video_ext.php',
    'https://vkvideo.ru/video_ext.php',
)

NUMERIC_ATTRS = {'width', 'height', 'colspan', 'rowspan', 'start'}


def _clean_url(value, allow_mailto=False):
    """Вернуть URL, если он безопасен, иначе None."""
    # Убираем пробелы и управляющие символы: браузеры их игнорируют,
    # и через них можно спрятать "java\tscript:".
    url = ''.join(ch for ch in value if ch > ' ' and ch != '\x7f')
    if not url:
        return None

    if url.startswith('/') and not url.startswith('//'):
        return url  # ссылка внутри сайта

    scheme = urlsplit(url).scheme.lower()
    if scheme in ('http', 'https'):
        return url
    if allow_mailto and scheme == 'mailto':
        return url
    return None


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open_tags = []   # стек открытых разрешённых тегов
        self.drop_depth = 0   # глубина внутри <script>/<style>/...

    # --- теги ---------------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT_TAGS:
            self.drop_depth += 1
            return
        if self.drop_depth or tag not in ALLOWED_TAGS:
            return

        clean_attrs = self._clean_attrs(tag, attrs)
        if clean_attrs is None:  # например, iframe с чужого сайта
            return

        rendered = ''.join(
            f' {name}' if value is None else f' {name}="{escape(value)}"'
            for name, value in clean_attrs
        )
        self.out.append(f'<{tag}{rendered}>')

        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        # <br/>, <img .../>
        if tag in DROP_CONTENT_TAGS:
            return
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and self.open_tags and self.open_tags[-1] == tag:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS:
            self.drop_depth = max(0, self.drop_depth - 1)
            return
        if self.drop_depth or tag not in self.open_tags:
            return
        # Закрываем все теги до нужного, чтобы разметка осталась корректной
        while self.open_tags:
            current = self.open_tags.pop()
            self.out.append(f'</{current}>')
            if current == tag:
                break

    # --- текст --------------------------------------------------------------

    def handle_data(self, data):
        if not self.drop_depth:
            self.out.append(escape(data, quote=False))

    # Комментарии, <!DOCTYPE>, <?...?> просто отбрасываются
    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        pass

    def handle_pi(self, data):
        pass

    def unknown_decl(self, data):
        pass

    # --- атрибуты -----------------------------------------------------------

    def _clean_attrs(self, tag, attrs):
        allowed = ALLOWED_ATTRS.get(tag, set())
        result = []
        has_src = False

        for name, value in attrs:
            name = name.lower()
            if name not in allowed:
                continue

            if name in NUMERIC_ATTRS:
                value = (value or '').strip().rstrip('%').rstrip('px')
                if not value.isdigit():
                    continue

            elif name == 'href':
                value = _clean_url(value or '', allow_mailto=True)
                if value is None:
                    continue

            elif name == 'src':
                value = _clean_url(value or '')
                if value is None:
                    continue
                if tag == 'iframe' and not value.startswith(VIDEO_EMBED_PREFIXES):
                    continue
                has_src = True

            elif name == 'target':
                if value != '_blank':
                    continue

            elif name == 'allowfullscreen':
                value = None

            result.append((name, value))

        if tag in ('img', 'iframe') and not has_src:
            return None

        if tag == 'a' and any(n == 'target' for n, _ in result):
            result.append(('rel', 'noopener noreferrer'))

        if tag == 'iframe':
            if not any(n == 'allowfullscreen' for n, _ in result):
                result.append(('allowfullscreen', None))
            result.append(('frameborder', '0'))

        return result

    def result(self):
        self.close()
        while self.open_tags:
            self.out.append(f'</{self.open_tags.pop()}>')
        return ''.join(self.out)


def sanitize_html(html):
    """Очистить HTML из редактора: оставить только безопасную разметку."""
    if not html:
        return ''
    parser = _Sanitizer()
    parser.feed(html)
    return parser.result().strip()
