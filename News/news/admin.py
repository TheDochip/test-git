from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ActivationCode, Category, Comment, Post, PostBlock, PostReaction, Profile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'email_verified', 'is_staff', 'date_joined')
    list_filter = UserAdmin.list_filter + ('email_verified',)
    fieldsets = UserAdmin.fieldsets + (
        ('Vibes', {'fields': ('email_verified', 'subscribed_categories', 'subscribed_authors')}),
    )
    filter_horizontal = UserAdmin.filter_horizontal + ('subscribed_categories', 'subscribed_authors')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'show_subscriptions')
    search_fields = ('user__username',)
    list_select_related = ('user',)


@admin.register(ActivationCode)
class ActivationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'expires_at', 'is_used', 'attempts')
    list_filter = ('is_used',)
    # Раньше здесь был user__username, но поля user у модели больше нет, и поиск падал.
    search_fields = ('email',)
    readonly_fields = ('code', 'created_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class PostBlockInline(admin.StackedInline):
    model = PostBlock
    extra = 0
    fields = ('position', 'block_type', 'content', 'file')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at', 'updated_at', 'likes', 'dislikes')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'author__username')
    list_select_related = ('author', 'category')
    readonly_fields = ('likes', 'dislikes', 'created_at', 'updated_at')
    inlines = [PostBlockInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    search_fields = ('content', 'author__username', 'post__title')
    list_select_related = ('author', 'post')


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'is_like')
    list_filter = ('is_like',)
    list_select_related = ('user', 'post')
