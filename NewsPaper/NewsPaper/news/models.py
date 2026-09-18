from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    bio = models.TextField(null=True, blank=True, verbose_name=_('Биография'))
    avatar = models.ImageField(upload_to='avatars/', blank=True, verbose_name=_('Аватар'))
    timezone = models.CharField(max_length=50, default='Europe/Moscow')
    theme = models.CharField(max_length=10, default='light')

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = _('Профиль')
        verbose_name_plural = _('Профили')


class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    rating = models.IntegerField(default=0, verbose_name=_('Рейтинг'))

    def __str__(self):
        return self.user.username

    def update_rating(self):
        from .models import Comment  # избегаем циклического импорта
        posts_rating = self.post_set.aggregate(total=models.Sum('rating'))['total'] or 0
        posts_rating *= 3
        comments_rating = self.user.comment_set.aggregate(total=models.Sum('rating'))['total'] or 0
        comments_to_posts_rating = Comment.objects.filter(post__author=self).aggregate(total=models.Sum('rating'))['total'] or 0
        self.rating = posts_rating + comments_rating + comments_to_posts_rating
        self.save()

    class Meta:
        verbose_name = _('Автор')
        verbose_name_plural = _('Авторы')


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Название'))
    subscribers = models.ManyToManyField(User, related_name='subscribers_category', verbose_name=_('Подписчики'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')


class Subscriber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('Категория'))
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата подписки'))

    def __str__(self):
        return f'{self.user.username} → {self.category.name}'

    class Meta:
        unique_together = ('user', 'category')
        verbose_name = _('Подписка')
        verbose_name_plural = _('Подписки')


class Post(models.Model):
    ARTICLE = 'article'
    NEWS = 'news'
    POST_TYPES = [
        (ARTICLE, _('Статья')),
        (NEWS, _('Новость')),
    ]

    author = models.ForeignKey(Author, on_delete=models.CASCADE, verbose_name=_('Автор'))
    post_type = models.CharField(
        max_length=10,
        choices=POST_TYPES,
        default=ARTICLE,
        verbose_name=_('Тип поста')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    categories = models.ManyToManyField(Category, through='PostCategory', verbose_name=_('Категории'))
    title = models.CharField(max_length=100, verbose_name=_('Заголовок'))
    text = models.TextField(verbose_name=_('Текст'))
    rating = models.IntegerField(default=0, verbose_name=_('Рейтинг'))

    def like(self):
        self.rating += 1
        self.save()

    def dislike(self):
        self.rating -= 1
        self.save()

    def preview(self):
        if len(self.text) > 124:
            return self.text[:124] + '...'
        return self.text

    def __str__(self):
        return f'{self.title[:50]}...' if len(self.title) > 50 else self.title

    class Meta:
        verbose_name = _('Пост')
        verbose_name_plural = _('Посты')


class PostCategory(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name=_('Пост'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('Категория'))

    class Meta:
        verbose_name = _('Связь поста и категории')
        verbose_name_plural = _('Связи постов и категорий')


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name=_('Пост'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    text = models.TextField(verbose_name=_('Текст комментария'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    rating = models.IntegerField(default=0, verbose_name=_('Рейтинг'))

    def like(self):
        self.rating += 1
        self.save()

    def dislike(self):
        self.rating -= 1
        self.save()

    class Meta:
        verbose_name = _('Комментарий')
        verbose_name_plural = _('Комментарии')


class ActivationCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    code = models.TextField(verbose_name=_('Код активации'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))

    def __str__(self):
        return f'{self.user.username} - {self.code}'

    class Meta:
        verbose_name = _('Код активации')
        verbose_name_plural = _('Коды активации')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

