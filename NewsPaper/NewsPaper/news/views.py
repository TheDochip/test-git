from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Post
from .filters import PostFilter
from django_filters.views import FilterView
from .forms import PostForm

class NewsList(ListView):
    model = Post
    template_name = 'news_list.html'
    context_object_name = 'news'
    ordering = ['-created_at']
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.filter(post_type='NW')


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

class NewsCreate(CreateView):
    model = Post
    form_class = PostForm
    template_name = 'post_edit.html'
    success_url = reverse_lazy('news_list')

    def form_valid(self, form):
        form.instance.post_type = 'NW'
        return super().form_valid(form)

class NewsUpdate(UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'post_edit.html'
    success_url = reverse_lazy('news_list')

class NewsDelete(DeleteView):
    model = Post
    template_name = 'post_delete.html'
    success_url = reverse_lazy('news_list')