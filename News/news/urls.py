from django.urls import path
from . import views


urlpatterns = [
    path('', views.NewsList.as_view(), name='news_list'),
    path('search/', views.NewsSearch.as_view(), name='news_search'),
    path('post/<int:pk>/delete/', views.PostDelete.as_view(), name='post_delete'),
    path('post/<int:pk>/edit/', views.PostUpdate.as_view(), name='post_edit'),
    path('post/<int:pk>/like/', views.PostLikeView.as_view(), name='post_like'),
    path('post/<int:pk>/dislike/', views.PostDislikeView.as_view(), name='post_dislike'),
    path('post/<int:pk>/comment/', views.CommentCreate.as_view(), name='post_comment'),
    path('comment/<int:pk>/edit/', views.CommentUpdate.as_view(), name='comment_edit'),
    path('comment/<int:pk>/delete/', views.CommentDelete.as_view(), name='comment_delete'),
    path('post/<int:pk>/', views.NewsDetail.as_view(), name='news_detail'),
    path('post/create/', views.PostCreate.as_view(), name='post_create'),
    path('login/', views.UserLogin.as_view(), name='login'),
    path('logout/', views.UserLogout.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('register/email/', views.RegisterEmailView.as_view(), name='register_email'),
    path('register/email/add/', views.RegisterEmailAddView.as_view(), name='register_email_add'),
    path('register/email/verify/', views.RegisterEmailVerifyView.as_view(), name='register_email_verify'),
    path('register/email/resend/',views.ResendCodeView.as_view(),name='register_email_resend'),
    path('register/email/skip/', views.RegisterSkipEmailView.as_view(),name='register_email_skip'),
    path('profile/<username>/', views.UserProfile.as_view(), name='profile'),
    path('profile/<username>/edit/', views.ProfileUpdate.as_view(), name='profile_edit'),
    path('profile/<username>/subscriptions/', views.SubscriptionUpdate.as_view(), name='subscriptions'),
    path('password/change/', views.UserPasswordChange.as_view(), name='password_change'),
    path('password/reset/', views.UserPasswordReset.as_view(), name='password_reset'),
    path('password/reset/done/', views.UserPasswordResetDone.as_view(), name='password_reset_done'),
    path('password/reset/complete/', views.UserPasswordResetComplete.as_view(), name='password_reset_complete'),
    path('password/reset/<uidb64>/<token>/', views.UserPasswordResetConfirm.as_view(), name='password_reset_confirm'),
]