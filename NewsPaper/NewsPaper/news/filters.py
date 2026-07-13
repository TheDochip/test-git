import django_filters
from django_filters import DateFilter, CharFilter
from django import forms
from .models import Post

class PostFilter(django_filters.FilterSet):
    title = CharFilter(field_name='title', lookup_expr='icontains', label='Название')
    author__user__username = CharFilter(field_name='author__user__username', lookup_expr='icontains', label='Автор')
    created_at = DateFilter(
        field_name='created_at',
        lookup_expr='date__gte',
        label='Позже даты',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Post
        fields = ['title', 'author__user__username', 'created_at']