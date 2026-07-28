from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

@shared_task
def send_new_post_notification(post_id, category_id, user_email):
    from .models import Post, Category, User

    post = Post.objects.get(pk=post_id)
    category = Category.objects.get(pk=category_id)

    html = render_to_string('email/news_post_notification.html', {
        'post': post,
        'category': category,
        'link': f'http://127.0.0.1:8000/news/{post.id}/',
    })

    send_mail(
        subject = f'Новая статья в категории "{category.name}"',
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        html_message=html,
        fail_silently=False,

    )


@shared_task
def send_weekly_digest():
    from .models import Post, Category, User

    week_ago = timezone.now() - timedelta(days=7)
    new_posts = Post.objects.filter(created_at__gte=week_ago, post_type='NW')

    if not new_posts.exists():
        return 'Новых новостей за неделю нет'

    subscribers = User.objects.filter(
        category_in = Category.objects.filter(posts__in=new_posts)
    ).distinct()

    sent_count = 0

    for user in subscribers:
        if not user.email:
            continue

        user_categories = user.category_set.all()
        user_posts = new_posts.filter(categories__in=user_categories).distinct()

        if not user_posts.exists():
            continue

        html = render_to_string('email/weekly_digest.html', {
            'user': user,
            'posts': user_posts,
            'week_ago': week_ago,
        })

        send_mail(
            subject='Ваш еженедельный дайджест новостей',
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html
        )

        sent_count += 1

    return f'Дайджест отправлен {sent_count} подписчикам'