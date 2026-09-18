from django.utils import timezone

def author_status(request):
    if request.user.is_authenticated:
        is_author = request.user.groups.filter(name='authors').exists()
    else:
        is_author = False
    return {'is_author': is_author}

def user_theme(request):
    if request.user.is_authenticated:
        try:
            theme = requst.user.profile.theme
        except:
            theme = 'light'
    else:
        hour = timezone.now().hour
        theme = 'dark' if hour >= 6 else 'light'
    return {'theme': theme}