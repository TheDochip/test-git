"""Доска объявлений: объявления, отклики, загрузка картинок."""

import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .emails import send_new_reply_notification, send_reply_accepted_notification
from .forms import PostForm, ReplyForm
from .models import Post, Reply


# ---------------------------------------------------------------------------
# Объявления
# ---------------------------------------------------------------------------

def post_list(request):
    posts = Post.objects.select_related('author')

    category = request.GET.get('category', '')
    if category in Post.Category.values:
        posts = posts.filter(category=category)
    else:
        category = ''

    page = Paginator(posts, 10).get_page(request.GET.get('page'))

    return render(request, 'board/post_list.html', {
        'page': page,
        'categories': Post.Category.choices,
        'current_category': category,
    })


def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related('author'), pk=pk)
    user = request.user

    can_reply = user.is_authenticated and user != post.author
    already_replied = (
        can_reply and post.replies.filter(author=user).exists()
    )

    if request.method == 'POST':
        if not user.is_authenticated:
            return redirect(f"{reverse('login')}?next={post.get_absolute_url()}")
        if not can_reply:
            return HttpResponseForbidden('Нельзя откликнуться на своё объявление.')

        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = post
            reply.author = user
            reply.save()

            send_new_reply_notification(reply)

            messages.success(request, 'Отклик отправлен — автор получит письмо.')
            return redirect(post)
    else:
        form = ReplyForm()

    my_replies = (
        post.replies.filter(author=user) if user.is_authenticated else Reply.objects.none()
    )

    return render(request, 'board/post_detail.html', {
        'post': post,
        'form': form,
        'can_reply': can_reply,
        'already_replied': already_replied,
        'my_replies': my_replies,
    })


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Объявление опубликовано.')
            return redirect(post)
    else:
        form = PostForm()

    return render(request, 'board/post_form.html', {'form': form, 'is_new': True})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Объявление сохранено.')
            return redirect(post)
    else:
        form = PostForm(instance=post)

    return render(request, 'board/post_form.html', {
        'form': form,
        'post': post,
        'is_new': False,
    })


@login_required
@require_POST
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    messages.success(request, 'Объявление удалено.')
    return redirect('my_posts')


@login_required
def my_posts(request):
    posts = Post.objects.filter(author=request.user)
    return render(request, 'board/my_posts.html', {'posts': posts})


# ---------------------------------------------------------------------------
# Приватная страница откликов на мои объявления
# ---------------------------------------------------------------------------

@login_required
def my_replies(request):
    my_posts_qs = Post.objects.filter(author=request.user).only('id', 'title')
    replies = (
        Reply.objects
        .filter(post__author=request.user)
        .select_related('post', 'author')
    )

    selected_post = None
    post_id = request.GET.get('post')
    if post_id:
        selected_post = my_posts_qs.filter(pk=post_id).first() if post_id.isdigit() else None
        if selected_post:
            replies = replies.filter(post=selected_post)

    status = request.GET.get('status', '')
    if status == 'new':
        replies = replies.filter(is_accepted=False)
    elif status == 'accepted':
        replies = replies.filter(is_accepted=True)
    else:
        status = ''

    return render(request, 'board/my_replies.html', {
        'replies': replies,
        'my_posts': my_posts_qs,
        'selected_post': selected_post,
        'status': status,
    })


def _redirect_back_to_replies(request):
    """Вернуться на страницу откликов, сохранив фильтры."""
    query = request.POST.get('return_query', '')
    url = reverse('my_replies')
    return redirect(f'{url}?{query}' if query else url)


@login_required
@require_POST
def reply_accept(request, pk):
    reply = get_object_or_404(
        Reply.objects.select_related('post', 'author'),
        pk=pk,
        post__author=request.user,
    )

    if not reply.is_accepted:
        reply.is_accepted = True
        reply.accepted_at = timezone.now()
        reply.save(update_fields=['is_accepted', 'accepted_at'])
        send_reply_accepted_notification(reply)
        messages.success(
            request,
            f'Отклик от {reply.author.username} принят — ему отправлено уведомление.'
        )

    return _redirect_back_to_replies(request)


@login_required
@require_POST
def reply_delete(request, pk):
    reply = get_object_or_404(Reply, pk=pk, post__author=request.user)
    reply.delete()
    messages.success(request, 'Отклик удалён.')
    return _redirect_back_to_replies(request)


# ---------------------------------------------------------------------------
# Загрузка картинок из редактора
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_FORMATS = {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif', 'WEBP': 'webp'}


@login_required
@require_POST
def upload_image(request):
    """
    Принимает картинку из редактора TinyMCE и возвращает {"location": url}.
    Проверяем, что это действительно картинка, а не файл с другим содержимым.
    """
    from PIL import Image, UnidentifiedImageError

    upload = request.FILES.get('file')
    if upload is None:
        return JsonResponse({'error': 'Файл не передан.'}, status=400)

    if upload.size > settings.POST_IMAGE_MAX_SIZE:
        max_mb = settings.POST_IMAGE_MAX_SIZE // (1024 * 1024)
        return JsonResponse({'error': f'Картинка больше {max_mb} МБ.'}, status=400)

    try:
        image = Image.open(upload)
        image_format = image.format
        image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        return JsonResponse({'error': 'Это не картинка.'}, status=400)

    extension = ALLOWED_IMAGE_FORMATS.get(image_format)
    if extension is None:
        return JsonResponse({'error': 'Поддерживаются JPG, PNG, GIF и WEBP.'}, status=400)

    upload.seek(0)
    path = default_storage.save(
        f'posts/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.{extension}',
        upload,
    )
    return JsonResponse({'location': default_storage.url(path)})
