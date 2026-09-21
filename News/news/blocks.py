"""
Разбор и сохранение блоков публикации из конструктора (templates/news/post_edit.html).

Конструктор отправляет поля вида:
    block_<N>_type         тип блока (text, image, ...)
    block_<N>_content      текст / ссылка / цитата
    block_<N>_file         загруженный файл
    block_<N>_existing_id  id уже сохранённого блока (при редактировании)

N идёт по порядку блоков на странице, из него берётся position.
"""
import re
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

from .models import PostBlock
from .validators import (
    clean_rich_text,
    validate_document_upload,
    validate_http_url,
    validate_image_upload,
    validate_video_upload,
)


BLOCK_TYPE_RE = re.compile(r'^block_(\d+)_type$')

BLOCK_TYPE_NAMES = dict(PostBlock.BLOCK_TYPES)

FILE_VALIDATORS = {
    'image': validate_image_upload,
    'video': validate_video_upload,
    'file': validate_document_upload,
}


@dataclass
class BlockData:
    index: int
    block_type: str
    content: str = ''
    upload: object = None           # новый загруженный файл
    existing: PostBlock = None      # уже сохранённый блок этого поста
    errors: list = field(default_factory=list)

    @property
    def keeps_existing_file(self):
        return (
            self.upload is None
            and self.existing is not None
            and self.existing.block_type == self.block_type
            and bool(self.existing.file)
        )


def parse_blocks(post_data, files, existing_blocks):
    """
    Собирает блоки из POST/FILES. existing_blocks: {str(id): PostBlock} блоков ЭТОГО поста,
    так что id чужого блока из формы просто игнорируется.
    """
    indexes = sorted(
        int(match.group(1))
        for key in post_data.keys()
        if (match := BLOCK_TYPE_RE.match(key))
    )

    blocks = []
    for index in indexes:
        prefix = f'block_{index}_'
        existing_id = post_data.get(prefix + 'existing_id', '')
        blocks.append(BlockData(
            index=index,
            block_type=post_data.get(prefix + 'type', ''),
            content=post_data.get(prefix + 'content', '').strip(),
            upload=files.get(prefix + 'file'),
            existing=existing_blocks.get(existing_id),
        ))
    return blocks


def validate_blocks(blocks):
    """
    Проверяет и нормализует блоки. Возвращает (годные_блоки, список_ошибок).
    Пустые текстовые блоки и цитаты молча отбрасываются.
    """
    valid, errors = [], []

    for number, block in enumerate(blocks, start=1):
        name = BLOCK_TYPE_NAMES.get(block.block_type)
        label = f'Блок {number} ({name or block.block_type})'

        if name is None:
            errors.append(f'{label}: неизвестный тип блока.')
            continue

        if block.block_type == 'text':
            block.content = clean_rich_text(block.content)
            if not strip_tags(block.content).strip():
                continue

        elif block.block_type == 'quote':
            if not block.content:
                continue

        elif block.block_type == 'link':
            try:
                validate_http_url(block.content)
            except ValidationError as error:
                errors.append(f'{label}: {error.messages[0]}')
                continue

        elif block.block_type == 'divider':
            block.content = ''

        if block.block_type in PostBlock.FILE_BLOCK_TYPES:
            block.content = ''
            if block.upload is not None:
                try:
                    FILE_VALIDATORS[block.block_type](block.upload)
                except ValidationError as error:
                    errors.append(f'{label}: {error.messages[0]}')
                    continue
            elif not block.keeps_existing_file:
                errors.append(f'{label}: прикрепите файл.')
                continue

        valid.append(block)

    if not errors and not any(block.block_type != 'divider' for block in valid):
        errors.append('Добавьте в публикацию хотя бы один блок с содержимым.')

    return valid, errors


def save_blocks(post, blocks, existing_blocks):
    """
    Сохраняет блоки: существующие обновляются на месте, новые создаются,
    а блоки, которых больше нет в форме, удаляются.
    """
    kept_ids = set()

    for position, data in enumerate(blocks):
        block = data.existing if data.existing is not None else PostBlock(post=post)

        block.block_type = data.block_type
        block.content = data.content
        block.position = position

        if data.upload is not None:
            block.file = data.upload
        elif not data.keeps_existing_file:
            block.file = None

        block.save()
        kept_ids.add(block.pk)

    for block in existing_blocks.values():
        if block.pk not in kept_ids:
            block.delete()


def serialize_saved_blocks(post):
    """Блоки поста в формате, который понимает JS конструктора."""
    return [
        {
            'id': block.id,
            'type': block.block_type,
            'content': block.content,
            'file_url': block.file.url if block.file else '',
            'file_name': block.file.name.split('/')[-1] if block.file else '',
        }
        for block in post.blocks.all()
    ]


def serialize_submitted_blocks(blocks):
    """
    Блоки из отправленной формы, чтобы при ошибке пользователь не потерял набранное.
    Новые загруженные файлы браузер заново не подставит, их придётся выбрать ещё раз.
    """
    result = []
    for block in blocks:
        content = block.content
        if block.block_type == 'text':
            # JS вставляет текст как HTML, поэтому отдаём только очищенный вариант.
            content = clean_rich_text(content)

        item = {'type': block.block_type, 'content': content, 'file_url': '', 'file_name': ''}
        if block.existing is not None:
            item['id'] = block.existing.id
            if block.keeps_existing_file:
                item['file_url'] = block.existing.file.url
                item['file_name'] = block.existing.file.name.split('/')[-1]
        result.append(item)
    return result
