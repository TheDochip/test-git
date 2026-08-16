from modeltranslation.translator import TranslationOptions, register
from .models import Post, Category

@register(Post)
class PostTranslationOptions(TranslationOptions):
    fields = ('title', 'text')

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name',)