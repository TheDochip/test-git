from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
    View,
)

from .activation import ActivationError, check_activation_code, send_activation_code
from .blocks import (
    parse_blocks,
    save_blocks,
    serialize_saved_blocks,
    serialize_submitted_blocks,
    validate_blocks,
)
from .forms import (
    ActivationCodeForm,
    AddEmailForm,
    CommentForm,
    PostForm,
    ProfileForm,
    RegistrationForm,
    SubscriptionForm,
)
from .models import Category, Comment, Post, PostBlock, PostReaction, Profile, User


# ============================================================
# ОБЩИЕ МИКСИНЫ
# ============================================================

class AuthorRequiredMixin(LoginRequiredMixin):
    """Редактировать и удалять объект может только его автор."""

    author_field = 'author'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if getattr(obj, self.author_field) != self.request.user:
            raise PermissionDenied
        return obj


class OwnProfileMixin(LoginRequiredMixin):
    """Страницы /profile/<username>/... доступны только самому пользователю."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and kwargs.get('username') != request.user.username:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class PostFilterMixin:
    """Фильтры по GET-параметрам q, category, date_from, date_to. Общие для ленты и поиска."""

    def get_filtered_queryset(self):
        queryset = (
            Post.objects
            .select_related('author', 'author__profile', 'category')
            # Блоки нужны карточкам для анонса; только текстовые, чтобы не тянуть лишнее.
            .prefetch_related(Prefetch(
                'blocks',
                queryset=PostBlock.objects.filter(block_type__in=['text', 'quote']),
            ))
            .annotate(comment_count=Count('comments', distinct=True))
        )
        params = self.request.GET

        query = params.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(blocks__block_type__in=['text', 'quote'], blocks__content__icontains=query)
            ).distinct()

        category = params.get('category', '')
        if category.isdigit():
            queryset = queryset.filter(category_id=category)

        # parse_date возвращает None для мусора вместо исключения (раньше это был 500).
        try:
            date_from = parse_date(params.get('date_from', ''))
            date_to = parse_date(params.get('date_to', ''))
        except ValueError:
            date_from = date_to = None

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by('-created_at')

    def get_filter_querystring(self):
        """GET-параметры без page, чтобы пагинация не сбрасывала фильтры."""
        params = self.request.GET.copy()
        params.pop('page', None)
        return params.urlencode()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['filter_querystring'] = self.get_filter_querystring()
        category = self.request.GET.get('category', '')
        context['current_category'] = (
            Category.objects.filter(pk=category).first() if category.isdigit() else None
        )
        return context


def redirect_back(request, fallback_url):
    """Возвращает на ?next=..., если это безопасный адрес нашего сайта."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect(fallback_url)


# ============================================================
# ЛЕНТА, ПОИСК, ПРОСМОТР
# ============================================================

class NewsList(PostFilterMixin, ListView):
    template_name = 'news/news_list.html'
    context_object_name = 'posts'
    paginate_by = 12
    popular_count = 3  # главный материал + два второстепенных

    def get_queryset(self):
        base_queryset = self.get_filtered_queryset()
        self.popular_posts = list(base_queryset.order_by('-likes', '-created_at')[:self.popular_count])
        # Популярные показываются в слайдере, в основной сетке их не дублируем.
        return base_queryset.exclude(pk__in=[post.pk for post in self.popular_posts])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = context.get('page_obj')
        context['popular_posts'] = self.popular_posts if page is None or page.number == 1 else []
        return context


class NewsSearch(PostFilterMixin, ListView):
    template_name = 'news/news_search.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        return self.get_filtered_queryset()


class NewsDetail(DetailView):
    template_name = 'news/news_detail.html'

    def get_queryset(self):
        return Post.objects.select_related('author', 'author__profile', 'category').prefetch_related(
            'blocks',
            Prefetch('comments', queryset=Comment.objects.select_related('author', 'author__profile')),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['reaction'] = (
            PostReaction.objects.filter(user=user, post=self.object).first()
            if user.is_authenticated else None
        )
        context['comment_form'] = CommentForm()
        context['more_posts'] = (
            Post.objects
            .filter(category=self.object.category)
            .exclude(pk=self.object.pk)
            .select_related('category', 'author')
            .order_by('-created_at')[:3]
        )
        return context


# ============================================================
# ПРОФИЛЬ И ПОДПИСКИ
# ============================================================

class UserProfile(DetailView):
    model = User
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'news/profile.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.object
        context['is_owner'] = self.request.user == profile_user
        context['posts'] = (
            profile_user.posts
            .select_related('category', 'author')
            .prefetch_related(Prefetch(
                'blocks', queryset=PostBlock.objects.filter(block_type__in=['text', 'quote']),
            ))
            .annotate(comment_count=Count('comments', distinct=True))
            .order_by('-created_at')
        )
        context['profile'], _ = Profile.objects.get_or_create(user=profile_user)
        return context


class ProfileUpdate(OwnProfileMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'news/profile_edit.html'

    def get_object(self, queryset=None):
        # Профиль мог не создаться, если пользователь появился до сигнала post_save.
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Профиль обновлён.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('profile', kwargs={'username': self.request.user.username})


class SubscriptionUpdate(OwnProfileMixin, FormView):
    template_name = 'news/subscriptions.html'
    form_class = SubscriptionForm

    def get_initial(self):
        initial = super().get_initial()
        initial['categories'] = self.request.user.subscribed_categories.all()
        return initial

    def form_valid(self, form):
        self.request.user.subscribed_categories.set(form.cleaned_data['categories'])
        messages.success(self.request, 'Подписки сохранены.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('profile', kwargs={'username': self.request.user.username})


# ============================================================
# ПУБЛИКАЦИИ
# ============================================================

class PostEditorMixin:
    """
    Общая логика создания и редактирования: форма поста + блоки конструктора.
    Пост и блоки сохраняются в одной транзакции.
    """

    form_class = PostForm
    template_name = 'news/post_edit.html'
    submitted_blocks = None

    def get_existing_blocks(self):
        if self.object is None or self.object.pk is None:
            return {}
        return {str(block.pk): block for block in self.object.blocks.all()}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object_for_edit()
        form = self.get_form()

        existing_blocks = self.get_existing_blocks()
        blocks = parse_blocks(request.POST, request.FILES, existing_blocks)
        valid_blocks, block_errors = validate_blocks(blocks)

        if not form.is_valid() or block_errors:
            for error in block_errors:
                form.add_error(None, error)
            self.submitted_blocks = serialize_submitted_blocks(blocks)
            return self.form_invalid(form)

        with transaction.atomic():
            if form.instance.author_id is None:
                form.instance.author = request.user
            self.object = form.save()
            save_blocks(self.object, valid_blocks, existing_blocks)

        messages.success(request, self.success_message)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.submitted_blocks is not None:
            context['existing_blocks'] = self.submitted_blocks
        elif self.object is not None:
            context['existing_blocks'] = serialize_saved_blocks(self.object)
        else:
            context['existing_blocks'] = []
        return context

    def get_success_url(self):
        return self.object.get_absolute_url()


class PostCreate(LoginRequiredMixin, PostEditorMixin, CreateView):
    success_message = 'Публикация создана.'

    def get_object_for_edit(self):
        return None


class PostUpdate(AuthorRequiredMixin, PostEditorMixin, UpdateView):
    model = Post
    success_message = 'Изменения сохранены.'

    def get_object_for_edit(self):
        return self.get_object()


class PostDelete(AuthorRequiredMixin, DeleteView):
    model = Post
    success_url = reverse_lazy('news_list')

    def form_valid(self, form):
        messages.success(self.request, 'Публикация удалена.')
        return super().form_valid(form)


class PostReactionView(LoginRequiredMixin, View):
    """
    Лайк/дизлайк. Повторное нажатие снимает реакцию, нажатие противоположной меняет её.
    Счётчики пересчитываются из таблицы реакций, поэтому не расходятся при двойных кликах.
    """

    is_like = True

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)

        try:
            with transaction.atomic():
                reaction = (
                    PostReaction.objects
                    .select_for_update()
                    .filter(user=request.user, post=post)
                    .first()
                )
                if reaction is None:
                    PostReaction.objects.create(user=request.user, post=post, is_like=self.is_like)
                elif reaction.is_like == self.is_like:
                    reaction.delete()
                else:
                    reaction.is_like = self.is_like
                    reaction.save(update_fields=['is_like'])
        except IntegrityError:
            # Параллельный запрос успел создать реакцию, повторно ничего не делаем.
            pass

        post.refresh_reaction_counts()
        return redirect_back(request, post.get_absolute_url())


class PostLikeView(PostReactionView):
    is_like = True


class PostDislikeView(PostReactionView):
    is_like = False


# ============================================================
# КОММЕНТАРИИ
# ============================================================

class CommentCreate(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        # Ищем пост уже после проверки логина (её делает LoginRequiredMixin.dispatch).
        self.post_object = get_object_or_404(Post, pk=kwargs['pk'])
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.post_object
        return super().form_valid(form)

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.post_object.get_absolute_url() + '#comments'


class CommentUpdate(AuthorRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm

    def get_success_url(self):
        return self.object.post.get_absolute_url() + '#comments'


class CommentDelete(AuthorRequiredMixin, DeleteView):
    model = Comment

    def get_success_url(self):
        return self.object.post.get_absolute_url() + '#comments'


# ============================================================
# ВХОД И РЕГИСТРАЦИЯ
# ============================================================

SESSION_USERNAME = 'username'
SESSION_PASSWORD_HASH = 'password_hash'
SESSION_EMAIL = 'email'


class UserLogin(LoginView):
    template_name = 'news/login.html'
    redirect_authenticated_user = True


class UserLogout(LogoutView):
    next_page = reverse_lazy('news_list')


class AnonymousOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('news_list')
        return super().dispatch(request, *args, **kwargs)


class RegistrationInProgressMixin(AnonymousOnlyMixin):
    """Шаги после первого экрана регистрации требуют имени и пароля в сессии."""

    require_email = False

    def dispatch(self, request, *args, **kwargs):
        session = request.session
        if not session.get(SESSION_USERNAME) or not session.get(SESSION_PASSWORD_HASH):
            messages.info(request, 'Начните регистрацию заново.')
            return redirect('register')
        if self.require_email and not session.get(SESSION_EMAIL):
            return redirect('register_email')
        return super().dispatch(request, *args, **kwargs)

    def create_user(self, email=None):
        """Создаёт пользователя из данных сессии. Возвращает None, если логин/email уже заняты."""
        session = self.request.session
        try:
            with transaction.atomic():
                user = User(
                    username=session[SESSION_USERNAME],
                    email=email,
                    email_verified=bool(email),
                    password=session[SESSION_PASSWORD_HASH],
                )
                user.save()
        except IntegrityError:
            return None
        finally:
            for key in (SESSION_USERNAME, SESSION_PASSWORD_HASH, SESSION_EMAIL):
                session.pop(key, None)
        return user


class RegisterView(AnonymousOnlyMixin, FormView):
    form_class = RegistrationForm
    template_name = 'news/register.html'

    def form_valid(self, form):
        # Пользователь создаётся только после шага с email, пока храним хеш пароля в сессии.
        self.request.session[SESSION_USERNAME] = form.cleaned_data['username']
        self.request.session[SESSION_PASSWORD_HASH] = make_password(form.cleaned_data['password'])
        self.request.session.pop(SESSION_EMAIL, None)
        return redirect('register_email')


class RegisterEmailView(RegistrationInProgressMixin, TemplateView):
    template_name = 'news/register_email.html'


class RegisterEmailAddView(RegistrationInProgressMixin, FormView):
    form_class = AddEmailForm
    template_name = 'news/register_email_add.html'

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            send_activation_code(email)
        except ActivationError as error:
            form.add_error('email', str(error))
            return self.form_invalid(form)

        self.request.session[SESSION_EMAIL] = email
        messages.success(self.request, f'Код отправлен на {email}.')
        return redirect('register_email_verify')


class RegisterEmailVerifyView(RegistrationInProgressMixin, FormView):
    form_class = ActivationCodeForm
    template_name = 'news/register_email_verify.html'
    require_email = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get(SESSION_EMAIL)
        return context

    def form_valid(self, form):
        email = self.request.session[SESSION_EMAIL]
        try:
            check_activation_code(email, form.cleaned_data['code'])
        except ActivationError as error:
            form.add_error('code', str(error))
            return self.form_invalid(form)

        if self.create_user(email=email) is None:
            messages.error(self.request, 'Этот логин или email уже заняли. Пройдите регистрацию заново.')
            return redirect('register')

        messages.success(self.request, 'Аккаунт создан, email подтверждён. Теперь можно войти.')
        return redirect('login')


class ResendCodeView(RegistrationInProgressMixin, View):
    require_email = True

    def post(self, request):
        email = request.session[SESSION_EMAIL]
        try:
            send_activation_code(email)
        except ActivationError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'Новый код отправлен на {email}.')
        return redirect('register_email_verify')


class RegisterSkipEmailView(RegistrationInProgressMixin, View):
    def post(self, request):
        if self.create_user(email=None) is None:
            messages.error(request, 'Этот логин уже заняли. Пройдите регистрацию заново.')
            return redirect('register')

        messages.success(request, 'Аккаунт создан. Теперь можно войти.')
        return redirect('login')


# ============================================================
# СМЕНА И ВОССТАНОВЛЕНИЕ ПАРОЛЯ
# ============================================================

class UserPasswordChange(LoginRequiredMixin, PasswordChangeView):
    template_name = 'news/user_password_change.html'

    def form_valid(self, form):
        # PasswordChangeView сам обновляет сессию, заново входить не нужно.
        messages.success(self.request, 'Пароль изменён.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('profile', kwargs={'username': self.request.user.username})


class UserPasswordReset(PasswordResetView):
    template_name = 'news/user_password_reset.html'
    email_template_name = 'news/user_password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


class UserPasswordResetDone(PasswordResetDoneView):
    template_name = 'news/user_password_reset_done.html'


class UserPasswordResetConfirm(PasswordResetConfirmView):
    template_name = 'news/user_password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class UserPasswordResetComplete(PasswordResetCompleteView):
    template_name = 'news/user_password_reset_complete.html'
