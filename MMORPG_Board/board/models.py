from django.conf import settings
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)


class ActivationCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activation_codes',
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.email} - {self.code}'



class Character(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='character',
    )

    name = models.CharField(
        max_length=50,
        unique=True
    )

    level = models.PositiveIntegerField(
        default=1,
    )

    experience = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    gold = models.PositiveIntegerField(
        default=0,
    )

    health = models.PositiveIntegerField(
        default=100
    )

    max_health = models.PositiveIntegerField(
        default=100
    )

    mana = models.PositiveIntegerField(
        default=50
    )

    max_mana = models.PositiveIntegerField(
        default=50
    )

    strength = models.PositiveIntegerField(
        default=10,
    )

    defense = models.PositiveIntegerField(
        default=5,
    )

    speed = models.PositiveIntegerField(
        default=5
    )

    stat_points = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return self.name



    @property
    def effective_strength(self):
        bonus = sum(
            entry.item.strength_bonus
            for entry in self.inventory.filter(
                is_equipped=True,
            ).select_related('item')
        )
        return self.strength + bonus

    @property
    def effective_defense(self):
        bonus = sum(
            entry.item.defense_bonus
            for entry in self.inventory.filter(
                is_equipped=True,
            ).select_related('item')
        )
        return self.defense + bonus

    @property
    def effective_speed(self):
        bonus = sum(
            entry.item.speed_bonus
            for entry in self.inventory.filter(
                is_equipped=True,
            ).select_related('item')
        )
        return self.speed + bonus


    def experience_to_next_level(self):
        return self.level * 100

    def add_experience(self, amount):
        self.experience += amount

        while self.experience >= self.experience_to_next_level():
            self.experience -= self.experience_to_next_level()
            self.level += 1
            self.stat_points += 3

            self.max_health += 20
            self.health = self.max_health

            self.max_mana += 10
            self.mana = self.max_mana

            self.strength += 2
            self.defense += 1
            self.speed += 1

        self.save()


class Quest(models.Model):
    title = models.CharField(
        max_length=150,
    )

    description = models.TextField()

    monster = models.ForeignKey(
        'Monster',
        on_delete=models.CASCADE,
        related_name='quests',
        null=True,
        blank=True,
    )

    target_amount = models.PositiveIntegerField(
        default=1,
    )

    experience_reward = models.PositiveIntegerField(
        default=0, )

    gold_reward = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title


class CharacterQuest(models.Model):
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name='quests',
    )

    quest = models.ForeignKey(
        Quest,
        on_delete=models.CASCADE,
        related_name='characters',
    )

    is_completed = models.BooleanField(
        default=False
    )

    progress = models.PositiveIntegerField(
        default=0,
    )

    accepted_at = models.DateTimeField(
        auto_now_add=True
    )

    completes_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['character', 'quest'],
                name='unique_character_quest'
            )
        ]

    def __str__(self):
        return f'{self.character.name} - {self.quest.title}'





class Monster(models.Model):
    name = models.CharField(
        max_length=50,
    )

    health = models.PositiveIntegerField(
        default=100,
    )

    is_defeated = models.BooleanField(
        default=False
    )

    attack = models.PositiveIntegerField(
        default=10,
    )

    defense = models.PositiveIntegerField(
        default=5,
    )

    speed = models.PositiveIntegerField(
        default=5,
    )

    experience_reward = models.PositiveIntegerField(
        default=0,
    )

    gold_reward = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return self.name




class Battle(models.Model):
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name='battles',
    )

    monster = models.ForeignKey(
        Monster,
        on_delete=models.CASCADE,
        related_name='battles',
    )

    monster_health = models.PositiveIntegerField()

    is_finished = models.BooleanField(
        default=False,
    )

    is_won = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f'{self.character.name} vs {self.monster.name}'





class Item(models.Model):
    ITEM_TYPES = [
        ('weapon', 'Оружие'),
        ('armor', 'Броня'),
        ('potion', 'Зелье'),
        ('misc', 'Разное'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    drop_chance = models.PositiveIntegerField(default=30)
    drop_quantity = models.PositiveIntegerField(default=1)

    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPES,
        default='misc',
    )

    strength_bonus = models.PositiveIntegerField(default=0)
    defense_bonus = models.PositiveIntegerField(default=0)
    speed_bonus = models.PositiveIntegerField(default=0)

    heal_amount = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CharacterInventory(models.Model):
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name='inventory',
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='owners',
    )

    quantity = models.PositiveIntegerField(default=1)
    is_equipped = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['character', 'item'],
                name='unique_character_inventory_item',
            ),
        ]

    def __str__(self):
        return f'{self.character.name}: {self.item.name} x{self.quantity}'





class MonsterDrop(models.Model):
    monster = models.ForeignKey(
        Monster,
        on_delete=models.CASCADE,
        related_name='drops',
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='monster_drops',
    )
    drop_chance = models.PositiveIntegerField(default=30)
    drop_quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['monster', 'item'],
                name='unique_monster_drop_item',
            )
        ]

    def __str__(self):
        return f'{self.monster.name} → {self.item.name}'


# ---------------------------------------------------------------------------
# Доска объявлений
# ---------------------------------------------------------------------------

class Post(models.Model):
    """Объявление пользователя."""

    class Category(models.TextChoices):
        TANKS = 'tanks', 'Танки'
        HEALERS = 'healers', 'Хилы'
        DD = 'dd', 'ДД'
        TRADERS = 'traders', 'Торговцы'
        GUILDMASTERS = 'guildmasters', 'Гилдмастеры'
        QUESTGIVERS = 'questgivers', 'Квестгиверы'
        BLACKSMITHS = 'blacksmiths', 'Кузнецы'
        LEATHERWORKERS = 'leatherworkers', 'Кожевники'
        POTION_MAKERS = 'potion_makers', 'Зельевары'
        SPELL_MASTERS = 'spell_masters', 'Мастера заклинаний'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор',
    )
    title = models.CharField('Заголовок', max_length=200)
    # HTML из редактора: текст, картинки, встроенные видео.
    # Перед сохранением очищается от опасных тегов (см. sanitizer.py).
    content = models.TextField('Текст')
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=Category.choices,
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Изменено', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        from .sanitizer import sanitize_html

        self.content = sanitize_html(self.content)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.pk])


class Reply(models.Model):
    """Отклик на объявление (простой текст)."""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='Объявление',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='Автор',
    )
    text = models.TextField('Текст')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    is_accepted = models.BooleanField('Принят', default=False)
    accepted_at = models.DateTimeField('Когда принят', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'

    def __str__(self):
        return f'{self.author} → {self.post}'


class Newsletter(models.Model):
    """Новостная рассылка. Отправляется из админки."""

    subject = models.CharField('Тема', max_length=200)
    body = models.TextField('Текст письма')
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    sent_at = models.DateTimeField('Отправлена', null=True, blank=True)
    recipients_count = models.PositiveIntegerField('Получателей', default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'

    def __str__(self):
        return self.subject
