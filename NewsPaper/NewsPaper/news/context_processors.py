def author_status(request):
    if request.user.is_authenticated:
        is_author = request.user.groups.filter(name='authors').exists()
    else:
        is_author = False
    return {'is_author': is_author}