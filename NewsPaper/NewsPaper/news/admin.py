from django.contrib import admin
from .models import Post, category, Author, Subscriber

@admin.site.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id','title','author','post_type','created_at','rating')
    list_filter = ('post_type','created_at', 'categories')
    search_fields = ('title', 'text')
    ordering = ('-created_at',)
    filter_horizontal = ('categories',)

@admin.site.register(category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','name')
    list_filter = ('name',)

@admin.site.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id','user','rating')
    list_filter = ('name_username',)

@admin.site.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('id','user','category','subscribed_at')
    list_filter = ('category',)
