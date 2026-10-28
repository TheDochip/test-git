
from django.contrib import admin
from .models import *


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'item_type',
        'strength_bonus',
        'defense_bonus',
        'speed_bonus',
        'heal_amount',
    )

    list_filter = ('item_type',)
    search_fields = ('name',)


@admin.register(CharacterInventory)
class CharacterInventoryAdmin(admin.ModelAdmin):
    list_display = (
        'character',
        'item',
        'quantity',
        'is_equipped',
    )

    list_filter = ('is_equipped',)
    search_fields = ('character__name', 'item__name')


@admin.register(MonsterDrop)
class MonsterDropAdmin(admin.ModelAdmin):
    list_display = (
        'monster',
        'item',
        'drop_chance',
        'drop_quantity',
    )
    list_filter = ('monster',)
    search_fields = ('monster__name', 'item__name')

# ---------------------------------------------------------------------------
# Пользователи и доска объявлений
# ---------------------------------------------------------------------------

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .emails import send_newsletter


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'email_verified', 'is_staff', 'date_joined')
    list_filter = BaseUserAdmin.list_filter + ('email_verified',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Подтверждение', {'fields': ('email_verified',)}),
    )


class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 0
    fields = ('author', 'text', 'is_accepted', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    inlines = [ReplyInline]


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'is_accepted', 'created_at')
    list_filter = ('is_accepted',)
    search_fields = ('text', 'author__username', 'post__title')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created_at', 'sent_at', 'recipients_count')
    readonly_fields = ('created_at', 'sent_at', 'recipients_count')
    actions = ['send_selected']

    @admin.action(description='Отправить выбранные рассылки всем пользователям')
    def send_selected(self, request, queryset):
        for newsletter in queryset:
            if newsletter.sent_at:
                self.message_user(
                    request,
                    f'«{newsletter}» уже отправлена '
                    f'{timezone.localtime(newsletter.sent_at):%d.%m.%Y %H:%M} — пропущена.',
                    level='warning',
                )
                continue
            count = send_newsletter(newsletter)
            self.message_user(request, f'«{newsletter}» отправлена, писем: {count}.')
