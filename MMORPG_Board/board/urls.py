from django.urls import path

from . import views_board
from .views import *

urlpatterns = [
    # Доска объявлений
    path('', views_board.post_list, name='home'),
    path('posts/new/', views_board.post_create, name='post_create'),
    path('posts/my/', views_board.my_posts, name='my_posts'),
    path('posts/<int:pk>/', views_board.post_detail, name='post_detail'),
    path('posts/<int:pk>/edit/', views_board.post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', views_board.post_delete, name='post_delete'),
    path('replies/', views_board.my_replies, name='my_replies'),
    path('replies/<int:pk>/accept/', views_board.reply_accept, name='reply_accept'),
    path('replies/<int:pk>/delete/', views_board.reply_delete, name='reply_delete'),
    path('upload-image/', views_board.upload_image, name='upload_image'),

    # Регистрация и вход
    path('register/', register, name='register'),
    path('verify-email/', verify_email, name='verify_email'),
    path('verify-email/resend/', resend_code, name='resend_code'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Игровая часть
    path('character/gain-experience/', gain_experience, name='gain_experience'),
    path('character/', character_view, name='character'),
    path('character/heal/', heal_character, name='heal_character'),
    path('character/restore-mana/', restore_mana, name='restore_mana'),
    path('character/increase-strength/', increase_strength, name='increase_strength'),
    path('character/increase-defense/', increase_defense, name='increase_defense'),
    path('character/increase-speed/', increase_speed, name='increase_speed'),
    path('battle/<int:monster_id>/', battle_view, name='battle'),
    path('battle/<int:monster_id>/start/', start_battle, name='start_battle'),
    path('battle/<int:monster_id>/attack/', attack_monster, name='attack_monster'),
    path('quests/<int:quest_id>/accept/', accept_quest, name='accept_quest'),
    path('quests/', quests_view, name='quests'),
    path('my_quests/', my_quests_view, name='my_quests'),
    path('my_quests/<int:quest_id>/complete/', complete_quest, name='complete_quest'),
    path('inventory/', inventory_view, name='inventory'),
    path('inventory/<int:inventory_id>/equip/', equip_item, name='equip_item',),
    path('inventory/<int:inventory_id>/unequip/', unequip_item, name='unequip_item',),
    path('inventory/<int:inventory_id>/use/', use_item, name='use_item',),
]
