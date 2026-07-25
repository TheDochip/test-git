from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from .models import Post, Profile, Category, ActivationCode
from .filters import PostFilter
from django_filters.views import FilterView
from .forms import PostForm, ProfileForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import uuid
from django.contrib.auth.forms import UserCreationForm

class NewsList(ListView):
    model = Post
    template_name = 'news_list.html'
    context_object_name = 'news'
    ordering = ['-created_at']
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.filter(post_type='NW')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context


class NewsDetail(DetailView):
    model = Post
    template_name = 'news_detail.html'
    context_object_name = 'news'

class NewsSearch(FilterView):
    model = Post
    template_name = 'news_search.html'
    context_object_name = 'news'
    filterset_class = PostFilter
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.filter(post_type='NW')

class NewsCreate(LoginRequiredMixin,PermissionRequiredMixin, CreateView):
    permission_required = 'news.add_post'
    model = Post
    form_class = PostForm
    template_name = 'post_edit.html'
    success_url = reverse_lazy('news_list')

    def form_valid(self, form):
        user = self.request.user
        author = user.author

        today = timezone.now().date()
        news_today = Post.objects.filter(
            author=author,
            post_type='NW',
            create_at__date=today,
        ).count()
        if news_today >= 3:
            form.add_error(None, f'Вы можете публиковать не более 3 новостей в сутки')
            return self.form_invalid(form)

        post = form.save(commit=False)
        post.author = author
        post.post_type = 'NW'
        post.save()
        form.save_m2m()


        for category in post.category.all():
            subscribers = category.subscribers.all()
            for user in subscribers:
                html_massage = render_to_string('email/new_post_notification.html', {
                    'user' : user,
                    'post' : post,
                    'category' : category,
                })
                send_mail(
                    subject = f'Новая новость в категории "{category.name}"',
                    message = '',
                    from_email = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [user.email],
                    html_message=html_massage,
                )
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='authors').exists():
            messages.error(request, 'Только авторы могут создавать новости.')
            return redirect('news_list')
        return super().dispatch(request, *args, **kwargs)

class NewsUpdate(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'news.change_post'
    model = Post
    form_class = PostForm
    template_name = 'post_edit.html'
    success_url = reverse_lazy('news_list')

class NewsDelete(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'news.delete_post'
    model = Post
    template_name = 'post_delete.html'
    success_url = reverse_lazy('news_list')

class ArticleUpdate(LoginRequiredMixin, UpdateView):
    permission_required = 'news.change_post'
    model = Post
    form_class = PostForm
    template_name = 'post_edit.html'
    success_url = reverse_lazy('news_list')




@login_required
def become_author(request):
    user = request.user
    author_group, _ = Group.objects.get_or_create(name='authors')
    if not user.groups.filter(name='authors').exists():
        user.groups.add(author_group)
        messages.success(request, 'Вы стали автором!')
    else:
        messages.info(request, 'Вы уже являетесь автором.')
    return redirect('news_list')

@login_required
def subscribe_to_category(request, pk):
    category = get_object_or_404(Category, id=pk)
    category.subscribers.add(request.user)
    return redirect('news_list')

@login_required
def unsubscribe_from_category(request, pk):
    category = get_object_or_404(Category, id=pk)
    category.subscribers.remove(request.user)
    return redirect('news_list')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            code = str(uuid.uuid4())
            ActivationCode.objects.create(user=user, code=code)

            subject = 'Добро пожаловать в News Portal'
            html_message = render_to_string('email/news_register.html', {
                'user' : user,
                'activation_url' : request.build_absolute_uri(f'/activate/{code}/'),
            })
            send_mail(
                subject = subject,
                message = '',
                from_email = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [user.email],
                html_message=html_message,
            )

            return redirect(request, ' registration/activation_sent.html')
        else:
            form = UserCreationForm()

        return render(request, 'registration/register.html', {'form': form})


def activate(request, code):
    try:
        activation = ActivationCode.objects.get(code=code)
        user = activation.user
        user.is_active = True
        user.save()
        activation.delete()
        return render(request, 'registration/activation-done.html', {'user': user})

    except ActivationCode.DoesNotExist:
        return render(request, 'registration/activation_invalid.html')




class ProfileView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'news.change_post'
    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user

        is_author = self.request.user.groups.filter(name='authors').exists()
        context['is_author'] = is_author

        return context

class ProfileUpdate(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'profile_update.html'
    success_url = reverse_lazy('news_list')