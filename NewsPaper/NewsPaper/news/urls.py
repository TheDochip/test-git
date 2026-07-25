from django.urls import path
from .views import NewsList, NewsDetail, NewsCreate, NewsUpdate, NewsDelete, NewsSearch, ArticleUpdate, become_author, ProfileView, subscribe_to_category, unsubscribe_from_category, register, activate
from django.urls import path, include



urlpatterns = [
    path('', NewsList.as_view(), name='news_list'),
    path('<int:pk>/', NewsDetail.as_view(), name='news_detail'),
    path('search/', NewsSearch.as_view(), name='news_search'),
    path('create/', NewsCreate.as_view(), name='news_create'),
    path('<int:pk>/update/', NewsUpdate.as_view(), name='news_update'),
    path('<int:pk>/delete/', NewsDelete.as_view(), name='news_delete'),
    path('<int:pk>/articles/', ArticleUpdate.as_view(), name='articles_update'),
    path('become_author/', become_author, name='become_author'),
    path('accounts/', include('allauth.urls')),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('category/<int:pk>/subscribe/', subscribe_to_category, name='subscribe'),
    path('category/<int:pk>/unsubscribe/', unsubscribe_from_category, name='unsubscribe'),
    path('register/', register, name='register'),
    path('activate/<str:code>/', activate, name='activate'),
]