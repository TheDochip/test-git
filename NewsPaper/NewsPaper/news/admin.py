from django.contrib import admin
from .models import Post, Category, Author, Subscriber

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'post_type', 'created_at', 'rating')
    list_filter = ('post_type', 'created_at', 'categories')
    search_fields = ('title', 'text')
    ordering = ('-created_at',)
    # filter_horizontal = ('categories',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rating')
    search_fields = ('user__username',)

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'subscribed_at')
    list_filter = ('category',)