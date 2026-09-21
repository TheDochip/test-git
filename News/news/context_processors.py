from .models import Category


def navigation(request):
    """Категории для меню в шапке и id выбранной категории для подсветки."""
    current = request.GET.get('category', '')
    return {
        'nav_categories': Category.objects.all(),
        'nav_current_category': current if current.isdigit() else '',
    }
