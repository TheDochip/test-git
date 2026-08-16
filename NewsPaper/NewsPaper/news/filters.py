import django_filters
from django_filters import DateFilter, CharFilter, ModelChoiceFilter
from django import forms
from .models import Post, Category
from django.utils.translation import gettext_lazy as _

class PostFilter(django_filters.FilterSet):
    title = CharFilter(
    field_name='title',
    lookup_expr='icontains',
    label=_('Название')
)

    author__user__username = CharFilter(
    field_name='author__user__username',
    lookup_expr='icontains',
    label=_('Автор')
)

    created_at = DateFilter(
    field_name='created_at',
    lookup_expr='date__gte',
    label=_('Позже даты'),
    widget=forms.DateInput(attrs={'type': 'date'})
)

    created_at_lte = DateFilter(
    field_name='created_at',
    lookup_expr='date__lte',
    label=_('Раньше даты'),
    widget=forms.DateInput(attrs={'type': 'date'})
)

    category = ModelChoiceFilter(
    field_name='categories',
    queryset=Category.objects.all(),
    label=_('Категория')
)

    post_type = django_filters.ChoiceFilter(
    field_name='post_type',
    choices=Post.POST_TYPES,
    label=_('Тип')
)


    class Meta:
        model = Post
        fields = ['title', 'author__user__username', 'created_at', 'created_at_lte', 'category', 'post_type']