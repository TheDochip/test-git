import html
import re

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator


class User(AbstractUser):
    email = models.EmailField(unique=True, blank=True, null=True)
    subscribed_categories = models.ManyToManyField('Category', blank=True, related_name='subscribers')
    subscribed_authors = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='subscribers')
    email_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Пустая строка из форм/админки ломает unique=True у второго пользователя без email.
        # NULL в уникальном поле может повторяться, поэтому храним отсутствие email как None.
        self.email = self.email.strip() if self.email else None
        super().save(*args, **kwargs)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars', blank=True)
    bio = models.TextField(blank=True)
    show_subscriptions = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=255)
    # Устаревшее поле: текст публикации теперь хранится в блоках (PostBlock).
    # Оставлено для старых постов, в новых остаётся пустым.
    content = models.TextField(blank=True)
    cover = models.ImageField(upload_to='posts/', blank=True, null=True)

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='posts')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Денормализованные счётчики. Пересчитываются из PostReaction в Post.refresh_reaction_counts,
    # поэтому не расходятся с реальными реакциями.
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news_detail', kwargs={'pk': self.pk})

    def plain_text(self):
        """Весь текст публикации без HTML: старое поле content + текстовые блоки и цитаты."""
        # blocks.all() использует prefetch_related, если он сделан во view.
        parts = [self.content] + [
            block.content for block in self.blocks.all() if block.block_type in ('text', 'quote')
        ]
        text = ' '.join(part for part in parts if part)
        # Пробел после закрывающих блочных тегов, иначе «абзац.Заголовок» склеится.
        text = re.sub(r'(</(?:p|h2|h3|li|blockquote|div)>|<br\s*/?>)', r'\1 ', text)
        return ' '.join(html.unescape(strip_tags(text)).split())

    def preview(self, words=28):
        return Truncator(self.plain_text()).words(words)

    def reading_minutes(self):
        words = len(self.plain_text().split())
        return max(1, round(words / 180))

    def refresh_reaction_counts(self):
        reactions = PostReaction.objects.filter(post=self)
        self.likes = reactions.filter(is_like=True).count()
        self.dislikes = reactions.filter(is_like=False).count()
        Post.objects.filter(pk=self.pk).update(likes=self.likes, dislikes=self.dislikes)


class PostBlock(models.Model):
    BLOCK_TYPES = [
        ('text', 'Текст'),
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('file', 'Файл'),
        ('link', 'Ссылки'),
        ('quote', 'Цитата'),
        ('divider', 'Разделитель'),
    ]
    FILE_BLOCK_TYPES = {'image', 'video', 'file'}

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='blocks')
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='post_files/', blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'{self.post.title} - {self.get_block_type_display()}'


class PostReaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    is_like = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_user_post_reaction'),
        ]


class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} → {self.post}'


class ActivationCode(models.Model):
    email = models.EmailField(db_index=True, null=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.email or 'Без email'

    @property
    def is_expired(self):
        return self.expires_at < timezone.now()

    @property
    def attempts_exhausted(self):
        return self.attempts >= settings.ACTIVATION_CODE_MAX_ATTEMPTS
