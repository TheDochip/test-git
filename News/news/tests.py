import io
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import ActivationCode, Category, Comment, Post, PostBlock, PostReaction, Profile, User


PASSWORD = 'Testpass123!'


def make_image(name='image.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password=PASSWORD, email='testuser@test.com')
        self.other_user = User.objects.create_user(username='otheruser', password=PASSWORD, email='otheruser@test.com')
        self.category = Category.objects.create(name='Test')
        self.post = Post.objects.create(title='Test', content='Test', author=self.user, category=self.category)

    def login(self, user=None):
        self.client.login(username=(user or self.user).username, password=PASSWORD)

    def assertLoginRequired(self, response, url):
        self.assertRedirects(response, reverse('login') + '?next=' + url, fetch_redirect_response=False)


# =====================================================================
# Регистрация
# =====================================================================

class RegistrationFormTest(TestCase):
    def test_weak_password_rejected(self):
        response = self.client.post(reverse('register'), {
            'username': 'weak', 'password': '1', 'password_confirm': '1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['password'])
        self.assertNotIn('username', self.client.session)

    def test_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'username': 'new', 'password': PASSWORD, 'password_confirm': PASSWORD + 'x',
        })
        self.assertContains(response, 'Пароли не совпадают')

    def test_username_case_insensitive_unique(self):
        User.objects.create_user(username='Ivan', password=PASSWORD)
        response = self.client.post(reverse('register'), {
            'username': 'ivan', 'password': PASSWORD, 'password_confirm': PASSWORD,
        })
        self.assertContains(response, 'уже существует')

    def test_valid_registration_goes_to_email_step(self):
        response = self.client.post(reverse('register'), {
            'username': 'new', 'password': PASSWORD, 'password_confirm': PASSWORD,
        })
        self.assertRedirects(response, reverse('register_email'))
        self.assertEqual(self.client.session['username'], 'new')
        self.assertFalse(User.objects.filter(username='new').exists())


class RegistrationSessionMixin:
    def start_registration(self, username='testuser', email=None):
        session = self.client.session
        session['username'] = username
        session['password_hash'] = make_password('testpassword123')
        if email:
            session['email'] = email
        session.save()


class RegisterSkipEmailTest(RegistrationSessionMixin, TestCase):
    def test_register_skip_email(self):
        session = self.client.session
        session['username'] = 'testuser'
        session['password_hash'] = 'test_password_hash'
        session.save()

        response = self.client.post(reverse('register_email_skip'))

        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='testuser')
        self.assertIsNone(user.email)
        self.assertFalse(user.email_verified)
        self.assertEqual(user.password, 'test_password_hash')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_skip_without_session_redirects_to_register(self):
        response = self.client.post(reverse('register_email_skip'))
        self.assertRedirects(response, reverse('register'))

    def test_username_taken_meanwhile(self):
        self.start_registration(username='taken')
        User.objects.create_user(username='taken', password=PASSWORD)
        response = self.client.post(reverse('register_email_skip'))
        self.assertRedirects(response, reverse('register'))


class RegisterEmailAddTest(RegistrationSessionMixin, TestCase):
    def test_sends_code(self):
        self.start_registration()
        response = self.client.post(reverse('register_email_add'), {'email': 'new@example.com'})
        self.assertRedirects(response, reverse('register_email_verify'))
        self.assertEqual(len(mail.outbox), 1)
        code = ActivationCode.objects.get(email='new@example.com').code
        self.assertIn(code, mail.outbox[0].body)

    def test_email_already_used(self):
        User.objects.create_user(username='u', password=PASSWORD, email='Busy@Example.com')
        self.start_registration()
        response = self.client.post(reverse('register_email_add'), {'email': 'busy@example.com'})
        self.assertContains(response, 'уже привязан')
        self.assertEqual(len(mail.outbox), 0)

    def test_requires_registration_session(self):
        response = self.client.get(reverse('register_email_add'))
        self.assertRedirects(response, reverse('register'))


class RegisterEmailVerifyTest(RegistrationSessionMixin, TestCase):
    email = 'test@example.com'

    def create_code(self, code='123456', expires_in=timedelta(days=1), **kwargs):
        return ActivationCode.objects.create(
            email=self.email, code=code, expires_at=timezone.now() + expires_in, **kwargs
        )

    def test_register_email_verify(self):
        self.start_registration(email=self.email)
        activation_code = self.create_code()

        response = self.client.post(reverse('register_email_verify'), {'code': '123456'})

        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, self.email)
        self.assertTrue(user.email_verified)
        self.assertTrue(check_password('testpassword123', user.password))

        activation_code.refresh_from_db()
        self.assertTrue(activation_code.is_used)

        session = self.client.session
        for key in ('email', 'username', 'password_hash'):
            self.assertNotIn(key, session)

    def test_register_email_verify_invalid_code(self):
        self.start_registration(email=self.email)
        self.create_code()

        response = self.client.post(reverse('register_email_verify'), {'code': '999999'})

        self.assertFalse(User.objects.filter(username='testuser').exists())
        self.assertContains(response, 'Неверный код')

    def test_register_email_verify_expired_code(self):
        self.start_registration(email=self.email)
        self.create_code(expires_in=-timedelta(days=1))

        response = self.client.post(reverse('register_email_verify'), {'code': '123456'})

        self.assertContains(response, 'Код просрочен')
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_attempts_are_limited(self):
        self.start_registration(email=self.email)
        self.create_code()

        for _ in range(5):
            self.client.post(reverse('register_email_verify'), {'code': '000000'})

        # Даже правильный код после исчерпания попыток не принимается.
        response = self.client.post(reverse('register_email_verify'), {'code': '123456'})
        self.assertContains(response, 'Слишком много неверных попыток')
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_verify_without_session_redirects(self):
        response = self.client.post(reverse('register_email_verify'), {'code': '123456'})
        self.assertRedirects(response, reverse('register'))


class ResendCodeTest(RegistrationSessionMixin, TestCase):
    email = 'test@example.com'

    def test_resend_code_create_new_code(self):
        self.start_registration(email=self.email)
        old = ActivationCode.objects.create(
            email=self.email, code='123456', expires_at=timezone.now() + timedelta(minutes=1)
        )
        # Код отправлен 2 минуты назад, ограничение в 60 секунд уже прошло.
        ActivationCode.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(minutes=2))

        self.client.post(reverse('register_email_resend'))

        codes = ActivationCode.objects.filter(email=self.email).order_by('created_at')
        self.assertEqual(codes.count(), 2)
        old.refresh_from_db()
        self.assertTrue(old.is_used)

        new_code = codes.last()
        self.assertFalse(new_code.is_used)
        self.assertGreater(new_code.expires_at, timezone.now())
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_cooldown(self):
        self.start_registration(email=self.email)
        ActivationCode.objects.create(
            email=self.email, code='123456', expires_at=timezone.now() + timedelta(minutes=5)
        )

        response = self.client.post(reverse('register_email_resend'), follow=True)

        self.assertContains(response, 'Новый код можно запросить через')
        self.assertEqual(ActivationCode.objects.filter(email=self.email).count(), 1)
        self.assertEqual(len(mail.outbox), 0)


# =====================================================================
# Пользователь и профиль
# =====================================================================

class UserModelTest(TestCase):
    def test_empty_email_saved_as_null(self):
        first = User.objects.create_user(username='a', password=PASSWORD, email='')
        second = User.objects.create_user(username='b', password=PASSWORD, email='')
        self.assertIsNone(first.email)
        self.assertIsNone(second.email)


class ProfileTest(BaseTestCase):
    def test_profile_page_public(self):
        response = self.client.get(reverse('profile', args=['testuser']))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Редактировать профиль')
        self.assertNotContains(response, 'testuser@test.com')

    def test_owner_sees_actions(self):
        self.login()
        response = self.client.get(reverse('profile', args=['testuser']))
        self.assertContains(response, 'Редактировать профиль')

    def test_profile_edit(self):
        self.login()
        url = reverse('profile_edit', args=['testuser'])
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(url, {'bio': 'Привет', 'avatar': make_image()})

        self.assertRedirects(response, reverse('profile', args=['testuser']))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.bio, 'Привет')
        self.assertTrue(profile.avatar)

    def test_profile_edit_rejects_non_image(self):
        self.login()
        fake = SimpleUploadedFile('avatar.png', b'not an image', content_type='image/png')
        response = self.client.post(reverse('profile_edit', args=['testuser']), {'avatar': fake})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_cannot_edit_other_profile(self):
        self.login(self.other_user)
        response = self.client.get(reverse('profile_edit', args=['testuser']))
        self.assertEqual(response.status_code, 403)

    def test_profile_edit_requires_login(self):
        url = reverse('profile_edit', args=['testuser'])
        self.assertLoginRequired(self.client.get(url), url)

    def test_subscriptions(self):
        self.login()
        url = reverse('subscriptions', args=['testuser'])
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(url, {'categories': [self.category.pk]})

        self.assertRedirects(response, reverse('profile', args=['testuser']))
        self.assertEqual(list(self.user.subscribed_categories.all()), [self.category])

    def test_logout_via_post(self):
        self.login()
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('news_list'))
        self.assertNotIn('_auth_user_id', self.client.session)


# =====================================================================
# Публикации
# =====================================================================

class PostCreateTest(BaseTestCase):
    def test_create_requires_login(self):
        url = reverse('post_create')
        self.assertLoginRequired(self.client.post(url, {'title': 'x'}), url)

    def test_create_with_blocks(self):
        self.login()
        response = self.client.post(reverse('post_create'), {
            'title': 'Новый пост',
            'category': self.category.pk,
            'cover': make_image('cover.png'),
            'block_0_type': 'text',
            'block_0_content': '<p>Привет <script>alert(1)</script></p>',
            'block_1_type': 'divider',
            'block_2_type': 'image',
            'block_2_file': make_image(),
            'block_3_type': 'link',
            'block_3_content': 'https://example.com',
        })

        post = Post.objects.get(title='Новый пост')
        self.assertRedirects(response, post.get_absolute_url())
        self.assertEqual(post.author, self.user)
        self.assertTrue(post.cover)
        self.assertEqual(
            list(post.blocks.values_list('block_type', flat=True)),
            ['text', 'divider', 'image', 'link'],
        )
        self.assertNotIn('<script>', post.blocks.get(block_type='text').content)

    def test_create_without_blocks_fails(self):
        self.login()
        response = self.client.post(reverse('post_create'), {'title': 'Пусто', 'category': self.category.pk})
        self.assertContains(response, 'хотя бы один блок')
        self.assertFalse(Post.objects.filter(title='Пусто').exists())

    def test_javascript_link_rejected(self):
        self.login()
        response = self.client.post(reverse('post_create'), {
            'title': 'XSS',
            'category': self.category.pk,
            'block_0_type': 'link',
            'block_0_content': 'javascript:alert(1)',
        })
        self.assertContains(response, 'http://')
        self.assertFalse(Post.objects.filter(title='XSS').exists())

    def test_dangerous_file_rejected(self):
        self.login()
        response = self.client.post(reverse('post_create'), {
            'title': 'HTML',
            'category': self.category.pk,
            'block_0_type': 'file',
            'block_0_file': SimpleUploadedFile('page.html', b'<script>alert(1)</script>'),
        })
        self.assertContains(response, 'Недопустимый формат')
        self.assertFalse(Post.objects.filter(title='HTML').exists())

    def test_blocks_kept_after_validation_error(self):
        self.login()
        response = self.client.post(reverse('post_create'), {
            'title': '',
            'category': self.category.pk,
            'block_0_type': 'quote',
            'block_0_content': 'Моя цитата',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['existing_blocks'][0]['content'], 'Моя цитата')


class PostUpdateTest(BaseTestCase):
    def edit(self, data):
        return self.client.post(reverse('post_edit', kwargs={'pk': self.post.pk}), {
            'title': 'Test', 'category': self.category.pk, **data,
        })

    def test_post_update_requires_login(self):
        url = reverse('post_edit', kwargs={'pk': self.post.pk})
        self.assertLoginRequired(self.client.get(url), url)

    def test_post_update_authenticated(self):
        self.login()
        response = self.client.get(reverse('post_edit', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 200)

    def test_post_update_forbidden_for_other_user(self):
        self.login(self.other_user)
        response = self.client.get(reverse('post_edit', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 403)

    def test_update_does_not_duplicate_blocks(self):
        block = PostBlock.objects.create(post=self.post, block_type='text', content='<p>one</p>', position=0)
        self.login()

        for text in ('<p>two</p>', '<p>three</p>', '<p>four</p>'):
            self.edit({
                'block_0_type': 'text',
                'block_0_content': text,
                'block_0_existing_id': str(block.pk),
            })

        self.assertEqual(self.post.blocks.count(), 1)
        block.refresh_from_db()
        self.assertEqual(block.content, '<p>four</p>')

    def test_update_reorders_adds_and_deletes(self):
        first = PostBlock.objects.create(post=self.post, block_type='text', content='<p>1</p>', position=0)
        second = PostBlock.objects.create(post=self.post, block_type='quote', content='2', position=1)
        removed = PostBlock.objects.create(post=self.post, block_type='quote', content='3', position=2)
        self.login()

        self.edit({
            'block_0_type': 'quote', 'block_0_content': '2', 'block_0_existing_id': str(second.pk),
            'block_1_type': 'text', 'block_1_content': '<p>1</p>', 'block_1_existing_id': str(first.pk),
            'block_2_type': 'divider',
        })

        blocks = list(self.post.blocks.all())
        self.assertEqual([b.pk for b in blocks[:2]], [second.pk, first.pk])
        self.assertEqual(blocks[2].block_type, 'divider')
        self.assertFalse(PostBlock.objects.filter(pk=removed.pk).exists())

    def test_existing_file_kept_without_new_upload(self):
        self.login()
        block = PostBlock.objects.create(post=self.post, block_type='image', file=make_image(), position=0)
        self.edit({'block_0_type': 'image', 'block_0_existing_id': str(block.pk)})
        block.refresh_from_db()
        self.assertTrue(block.file)

    def test_foreign_block_id_ignored(self):
        other_post = Post.objects.create(title='Other', author=self.other_user, category=self.category)
        foreign = PostBlock.objects.create(post=other_post, block_type='quote', content='чужой', position=0)
        self.login()

        self.edit({'block_0_type': 'quote', 'block_0_content': 'мой', 'block_0_existing_id': str(foreign.pk)})

        foreign.refresh_from_db()
        self.assertEqual(foreign.content, 'чужой')
        self.assertEqual(foreign.post, other_post)
        self.assertEqual(self.post.blocks.get().content, 'мой')


class PostDeleteTest(BaseTestCase):
    def test_post_delete(self):
        self.login()
        response = self.client.post(reverse('post_delete', kwargs={'pk': self.post.pk}))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())
        self.assertRedirects(response, reverse('news_list'))

    def test_post_delete_forbidden_for_other_user(self):
        self.login(self.other_user)
        response = self.client.post(reverse('post_delete', kwargs={'pk': self.post.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_post_delete_requires_login(self):
        url = reverse('post_delete', kwargs={'pk': self.post.pk})
        self.assertLoginRequired(self.client.get(url), url)


class PostDetailTest(BaseTestCase):
    def test_detail_page(self):
        PostBlock.objects.create(post=self.post, block_type='text', content='<p>Текст блока</p>')
        response = self.client.get(self.post.get_absolute_url())
        self.assertContains(response, 'Текст блока')

    def test_old_javascript_link_not_rendered(self):
        PostBlock.objects.create(post=self.post, block_type='link', content='javascript:alert(1)')
        response = self.client.get(self.post.get_absolute_url())
        self.assertNotContains(response, 'javascript:alert(1)')

    def test_missing_post_404(self):
        self.assertEqual(self.client.get(reverse('news_detail', args=[999])).status_code, 404)


# =====================================================================
# Реакции
# =====================================================================

class PostLikeTest(BaseTestCase):
    def like(self):
        return self.client.post(reverse('post_like', kwargs={'pk': self.post.pk}))

    def test_post_like(self):
        self.login()
        response = self.like()
        self.assertRedirects(response, self.post.get_absolute_url())
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)

    def test_post_like_requires_login(self):
        url = reverse('post_like', kwargs={'pk': self.post.pk})
        self.assertLoginRequired(self.client.post(url), url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 0)

    def test_post_like_toggle(self):
        self.login()
        self.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)

        self.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 0)

    def test_post_like_changes_dislike_to_like(self):
        self.login()
        PostReaction.objects.create(user=self.user, post=self.post, is_like=False)
        self.post.refresh_reaction_counts()

        self.like()

        self.post.refresh_from_db()
        self.assertEqual((self.post.likes, self.post.dislikes), (1, 0))
        self.assertTrue(PostReaction.objects.get(user=self.user, post=self.post).is_like)

    def test_like_missing_post_404(self):
        self.login()
        response = self.client.post(reverse('post_like', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)

    def test_counters_fixed_even_if_out_of_sync(self):
        Post.objects.filter(pk=self.post.pk).update(likes=42)
        self.login()
        self.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)


class PostDislikeTest(BaseTestCase):
    def test_post_dislike(self):
        self.login()
        response = self.client.post(reverse('post_dislike', kwargs={'pk': self.post.pk}))
        self.assertRedirects(response, self.post.get_absolute_url())
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 1)

    def test_post_dislike_requires_login(self):
        url = reverse('post_dislike', kwargs={'pk': self.post.pk})
        self.assertLoginRequired(self.client.post(url), url)
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 0)


# =====================================================================
# Комментарии
# =====================================================================

class CommentTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.comment = Comment.objects.create(author=self.user, post=self.post, content='Первый')

    def test_create_comment(self):
        self.login(self.other_user)
        response = self.client.post(reverse('post_comment', args=[self.post.pk]), {'content': 'Привет'})
        self.assertRedirects(response, self.post.get_absolute_url() + '#comments', fetch_redirect_response=False)
        self.assertTrue(Comment.objects.filter(author=self.other_user, content='Привет').exists())

    def test_comment_on_missing_post_404(self):
        self.login()
        response = self.client.post(reverse('post_comment', args=[999]), {'content': 'x'})
        self.assertEqual(response.status_code, 404)

    def test_delete_comment(self):
        self.login()
        url = reverse('comment_delete', args=[self.comment.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(url)

        self.assertRedirects(response, self.post.get_absolute_url() + '#comments', fetch_redirect_response=False)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_delete_comment_forbidden_for_other_user(self):
        self.login(self.other_user)
        response = self.client.post(reverse('comment_delete', args=[self.comment.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=self.comment.pk).exists())

    def test_edit_comment(self):
        self.login()
        self.client.post(reverse('comment_edit', args=[self.comment.pk]), {'content': 'Исправлено'})
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Исправлено')


# =====================================================================
# Лента и поиск
# =====================================================================

class NewsListTest(BaseTestCase):
    def test_popular_not_duplicated_and_paginated(self):
        for i in range(20):
            Post.objects.create(title=f'Post {i}', author=self.user, category=self.category)

        response = self.client.get(reverse('news_list'))

        popular_ids = {post.pk for post in response.context['popular_posts']}
        page_ids = {post.pk for post in response.context['posts']}
        self.assertEqual(len(popular_ids), 3)
        self.assertFalse(popular_ids & page_ids)
        self.assertTrue(response.context['is_paginated'])

        second_page = self.client.get(reverse('news_list') + '?page=2')
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.context['popular_posts'], [])

    def test_invalid_filters_do_not_crash(self):
        response = self.client.get(reverse('news_search') + '?date_from=2026-99-99&category=abc&q=test')
        self.assertEqual(response.status_code, 200)

    def test_search_in_block_text(self):
        post = Post.objects.create(title='Без совпадения', author=self.user, category=self.category)
        PostBlock.objects.create(post=post, block_type='text', content='<p>уникальноеслово</p>')

        response = self.client.get(reverse('news_search') + '?q=уникальноеслово')

        self.assertEqual([p.pk for p in response.context['posts']], [post.pk])
