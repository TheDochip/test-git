from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from news.models import Post, Category
from django.contrib.auth.models import User
from django_filters import filters

class Command(BaseCommand):
    def handle(self, *args, **options):
        week_ago = timezone.now() - timedelta(days=7)
        new_posts = Post.objects.filter(
            created_at__gte=week_ago,
            post_type='NW'
        )

        if not new_posts.exists():
            self.stdout.write('Новых статей за неделю нет')
            return

        subsribers = User.objects.filter(
            category__in=Category.objects.filter(
                post__in=new_posts
            )
        ).distinct()

        sent_count = 0

        for user in subsribers:
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
                subject='Ваш еженедельный дайджуст новостей',
                massage='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html,
                fail_silently=False,
            )
            sent_count += 1

        self.stdout.write(f'дайджест отправлен {sent_count} подписчикам ')