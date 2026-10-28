import io
import re
import shutil
import tempfile

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import ActivationCode, Newsletter, Post, Reply, User
from .sanitizer import sanitize_html
from .emails import send_newsletter

TEMP_MEDIA = tempfile.mkdtemp()


def make_user(username, verified=True):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='Str0ng-pass-123',
    )
    user.email_verified = verified
    user.save()
    return user


class RegistrationTests(TestCase):
    def test_register_sends_code_and_verify_logs_in(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbie',
            'email': 'Newbie@Example.com',
            'password': 'Str0ng-pass-123',
            'password_confirm': 'Str0ng-pass-123',
        })
        self.assertRedirects(response, reverse('verify_email'))

        user = User.objects.get(username='newbie')
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newbie@example.com'])

        code = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)

        # неверный код
        response = self.client.post(reverse('verify_email'), {'code': '000000' if code != '000000' else '111111'})
        self.assertContains(response, 'Неверный или просроченный код')

        response = self.client.post(reverse('verify_email'), {'code': code})
        self.assertRedirects(response, reverse('home'))
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_code_of_other_user_does_not_work(self):
        other = make_user('other', verified=False)
        ActivationCode.objects.create(
            user=other, code='123456',
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        self.client.post(reverse('register'), {
            'username': 'me', 'email': 'me@example.com',
            'password': 'Str0ng-pass-123', 'password_confirm': 'Str0ng-pass-123',
        })
        self.client.post(reverse('verify_email'), {'code': '123456'})
        other.refresh_from_db()
        self.assertFalse(other.email_verified)
        self.assertFalse(User.objects.get(username='me').email_verified)

    def test_unverified_login_sends_new_code(self):
        make_user('lazy', verified=False)
        response = self.client.post(reverse('login'), {
            'username': 'lazy', 'password': 'Str0ng-pass-123',
        })
        self.assertRedirects(response, reverse('verify_email'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn('_auth_user_id', self.client.session)


class PostTests(TestCase):
    def setUp(self):
        self.author = make_user('author')
        self.client.force_login(self.author)

    def test_anonymous_cannot_create(self):
        self.client.logout()
        response = self.client.get(reverse('post_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_create_requires_category(self):
        response = self.client.post(reverse('post_create'), {
            'title': 'Ищу хила', 'content': '<p>Текст</p>',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.exists())

    def test_create_and_sanitize(self):
        self.client.post(reverse('post_create'), {
            'title': 'Ищу хила',
            'category': Post.Category.HEALERS,
            'content': (
                '<p onclick="x()">Привет<script>alert(1)</script></p>'
                '<img src="/media/a.png" onerror="alert(1)">'
                '<iframe src="https://www.youtube.com/embed/abc"></iframe>'
            ),
        })
        post = Post.objects.get()
        self.assertEqual(post.author, self.author)
        self.assertNotIn('script', post.content)
        self.assertNotIn('onclick', post.content)
        self.assertNotIn('onerror', post.content)
        self.assertIn('<img src="/media/a.png">', post.content)
        self.assertIn('youtube.com/embed/abc', post.content)

    def test_only_author_can_edit(self):
        post = Post.objects.create(
            author=self.author, title='T', content='<p>x</p>', category='dd',
        )
        stranger = make_user('stranger')
        self.client.force_login(stranger)
        response = self.client.post(reverse('post_edit', args=[post.pk]), {
            'title': 'Взлом', 'category': 'dd', 'content': '<p>y</p>',
        })
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.author)
        self.client.post(reverse('post_edit', args=[post.pk]), {
            'title': 'Новый', 'category': 'tanks', 'content': '<p>y</p>',
        })
        post.refresh_from_db()
        self.assertEqual(post.title, 'Новый')
        self.assertEqual(post.category, 'tanks')

    def test_category_filter(self):
        Post.objects.create(author=self.author, title='Танк', content='x', category='tanks')
        Post.objects.create(author=self.author, title='Кузнец', content='x', category='blacksmiths')
        response = self.client.get(reverse('home'), {'category': 'tanks'})
        self.assertContains(response, 'Танк')
        self.assertNotContains(response, '>Кузнец<')


class ReplyTests(TestCase):
    def setUp(self):
        self.author = make_user('author')
        self.fan = make_user('fan')
        self.post = Post.objects.create(
            author=self.author, title='Ищу танка', content='<p>x</p>', category='tanks',
        )

    def test_reply_sends_email_to_author(self):
        self.client.force_login(self.fan)
        self.client.post(reverse('post_detail', args=[self.post.pk]), {'text': 'Я танк!'})
        reply = Reply.objects.get()
        self.assertEqual(reply.author, self.fan)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['author@example.com'])
        self.assertIn('Я танк!', mail.outbox[0].body)

    def test_cannot_reply_to_own_post(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse('post_detail', args=[self.post.pk]), {'text': 'сам себе'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Reply.objects.exists())

    def test_private_page_filter_accept_delete(self):
        other_post = Post.objects.create(
            author=self.author, title='Ищу кузнеца', content='x', category='blacksmiths',
        )
        r1 = Reply.objects.create(post=self.post, author=self.fan, text='отклик на танка')
        Reply.objects.create(post=other_post, author=self.fan, text='отклик на кузнеца')
        foreign_post = Post.objects.create(author=self.fan, title='Чужое', content='x', category='dd')
        foreign = Reply.objects.create(post=foreign_post, author=self.author, text='чужой отклик')

        # страница только для автора и только его объявления
        self.client.force_login(self.author)
        response = self.client.get(reverse('my_replies'))
        self.assertContains(response, 'отклик на танка')
        self.assertContains(response, 'отклик на кузнеца')
        self.assertNotContains(response, 'чужой отклик')

        response = self.client.get(reverse('my_replies'), {'post': self.post.pk})
        self.assertContains(response, 'отклик на танка')
        self.assertNotContains(response, 'отклик на кузнеца')

        # принятие — письмо автору отклика
        self.client.post(reverse('reply_accept', args=[r1.pk]))
        r1.refresh_from_db()
        self.assertTrue(r1.is_accepted)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['fan@example.com'])

        # повторное принятие не шлёт второе письмо
        self.client.post(reverse('reply_accept', args=[r1.pk]))
        self.assertEqual(len(mail.outbox), 1)

        # нельзя принять/удалить отклик на чужое объявление
        self.assertEqual(self.client.post(reverse('reply_accept', args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('reply_delete', args=[foreign.pk])).status_code, 404)

        self.client.post(reverse('reply_delete', args=[r1.pk]))
        self.assertFalse(Reply.objects.filter(pk=r1.pk).exists())

    def test_replies_page_requires_login(self):
        response = self.client.get(reverse('my_replies'))
        self.assertEqual(response.status_code, 302)


class NewsletterTests(TestCase):
    def test_sent_to_verified_users_separately(self):
        make_user('a')
        make_user('b')
        make_user('c', verified=False)
        newsletter = Newsletter.objects.create(subject='Обновление сервера', body='Новый рейд!')

        count = send_newsletter(newsletter)

        self.assertEqual(count, 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ['a@example.com', 'b@example.com'])
        newsletter.refresh_from_db()
        self.assertIsNotNone(newsletter.sent_at)
        self.assertEqual(newsletter.recipients_count, 2)

    def test_admin_action(self):
        admin = User.objects.create_superuser('boss', 'boss@example.com', 'Str0ng-pass-123')
        admin.email_verified = True
        admin.save()
        newsletter = Newsletter.objects.create(subject='Тема', body='Текст')
        self.client.force_login(admin)
        self.client.post(reverse('admin:board_newsletter_changelist'), {
            'action': 'send_selected', '_selected_action': [newsletter.pk],
        })
        self.assertEqual(len(mail.outbox), 1)
        # повторно не отправляется
        self.client.post(reverse('admin:board_newsletter_changelist'), {
            'action': 'send_selected', '_selected_action': [newsletter.pk],
        })
        self.assertEqual(len(mail.outbox), 1)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UploadTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.client.force_login(make_user('artist'))

    def test_upload_png(self):
        from PIL import Image

        buf = io.BytesIO()
        Image.new('RGB', (10, 10), 'red').save(buf, 'PNG')
        buf.seek(0)
        buf.name = 'pic.png'
        response = self.client.post(reverse('upload_image'), {'file': buf})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['location'].startswith('/media/posts/'))
        self.assertTrue(response.json()['location'].endswith('.png'))

    def test_reject_not_image(self):
        fake = io.BytesIO(b'<script>alert(1)</script>')
        fake.name = 'evil.png'
        response = self.client.post(reverse('upload_image'), {'file': fake})
        self.assertEqual(response.status_code, 400)


class SanitizerTests(TestCase):
    def test_cases(self):
        cases = {
            '<a href="javascript:alert(1)">x</a>': '<a>x</a>',
            '<a href="java\tscript:alert(1)">x</a>': '<a>x</a>',
            '<a href="https://ok.ru" target="_blank">x</a>':
                '<a href="https://ok.ru" target="_blank" rel="noopener noreferrer">x</a>',
            '<iframe src="https://evil.com/embed"></iframe>': '',
            '<img src="data:image/svg+xml;base64,AAA">': '',
            '<svg><script>alert(1)</script></svg>ok': 'ok',
            '<p>a < b & c</p>': '<p>a &lt; b &amp; c</p>',
            '<p><b>unclosed': '<p><b>unclosed</b></p>',
            '</div><p>x</p>': '<p>x</p>',
            '<style>body{}</style><p>x</p>': '<p>x</p>',
            '<img src=x onerror=alert(1)>': '',
            '<p title="&quot;><script>">x</p>': '<p>x</p>',
        }
        for dirty, clean in cases.items():
            with self.subTest(dirty=dirty):
                self.assertEqual(sanitize_html(dirty), clean)
