import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .emails import send_activation_code
from .forms import *
from .models import *

# id пользователя, который зарегистрировался, но ещё не ввёл код
PENDING_USER_SESSION_KEY = 'pending_user_id'
ACTIVATION_CODE_TTL = timedelta(minutes=10)


def create_and_send_activation_code(user):
    """Погасить старые коды, создать новый и отправить его на почту."""
    ActivationCode.objects.filter(user=user, is_used=False).update(is_used=True)

    code = f'{random.SystemRandom().randint(0, 999999):06d}'
    ActivationCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + ACTIVATION_CODE_TTL,
    )
    return send_activation_code(user, code)


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.email_verified = False
            user.save()

            Character.objects.create(
                user=user,
                name=user.username,
            )

            create_and_send_activation_code(user)
            request.session[PENDING_USER_SESSION_KEY] = user.pk

            messages.info(
                request,
                f'Мы отправили код подтверждения на {user.email}.'
            )
            return redirect('verify_email')
    else:
        form = RegistrationForm()

    return render(request, 'board/register.html', {'form': form})


def _pending_user(request):
    user_id = request.session.get(PENDING_USER_SESSION_KEY)
    if not user_id:
        return None
    return User.objects.filter(pk=user_id, email_verified=False).first()


def verify_email(request):
    pending_user = _pending_user(request)

    if pending_user is None:
        messages.info(
            request,
            'Войдите под своим логином — если e-mail не подтверждён, '
            'мы пришлём новый код.'
        )
        return redirect('login')

    if request.method == 'POST':
        form = EmailVerificationForm(request.POST)

        if form.is_valid():
            code = form.cleaned_data['code']

            activation = ActivationCode.objects.filter(
                user=pending_user,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).first()

            if activation:
                pending_user.email_verified = True
                pending_user.save(update_fields=['email_verified'])

                activation.is_used = True
                activation.save(update_fields=['is_used'])

                request.session.pop(PENDING_USER_SESSION_KEY, None)
                login(request, pending_user)

                messages.success(
                    request,
                    'E-mail подтверждён! Теперь вы можете размещать объявления.'
                )
                return redirect('home')

            form.add_error(
                'code',
                'Неверный или просроченный код.'
            )
    else:
        form = EmailVerificationForm()

    return render(
        request,
        'board/verify_email.html',
        {'form': form, 'pending_user': pending_user}
    )


def resend_code(request):
    if request.method != 'POST':
        return redirect('verify_email')

    pending_user = _pending_user(request)
    if pending_user is None:
        return redirect('login')

    last_code = pending_user.activation_codes.order_by('-created_at').first()
    if last_code and timezone.now() - last_code.created_at < timedelta(minutes=1):
        messages.warning(request, 'Новый код можно запросить через минуту.')
    else:
        create_and_send_activation_code(pending_user)
        messages.info(request, f'Новый код отправлен на {pending_user.email}.')

    return redirect('verify_email')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None:
                if not user.email_verified:
                    # Пароль верный, но почта не подтверждена —
                    # шлём свежий код и отправляем на страницу ввода
                    create_and_send_activation_code(user)
                    request.session[PENDING_USER_SESSION_KEY] = user.pk
                    messages.info(
                        request,
                        f'Сначала подтвердите e-mail: код отправлен на {user.email}.'
                    )
                    return redirect('verify_email')

                login(request, user)
                next_url = request.GET.get('next')
                if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                    return redirect(next_url)
                return redirect('home')
            else:
                form.add_error(
                    None,
                    'Неверное имя пользователя или пароль.'
                )
    else:
        form = LoginForm()

    return render(
        request,
        'board/login.html',
        {'form': form}
    )


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required(login_url='/login/')
def character_view(request):
    character = request.user.character
    return render(
        request,
        'board/character.html',
        {'character': character}
    )

@login_required(login_url='/login/')
def gain_experience(request):
    if request.method == 'POST':
        character = request.user.character
        character.add_experience(50)

    return redirect('character')


def quests_view(request):
    quests = Quest.objects.all()

    return render(
        request,
        'board/quests.html',
        {'quests': quests}
    )


@login_required(login_url='/login/')
def accept_quest(request, quest_id):
    if request.method == 'POST':
        quest = Quest.objects.get(id=quest_id)
        character = request.user.character

        CharacterQuest.objects.get_or_create(
            character = character,
            quest = quest,
        )

    return redirect('quests')


@login_required(login_url='/login/')
def my_quests_view(request):
    character = request.user.character

    character_quests = CharacterQuest.objects.filter(
        character = character,
    ).select_related('quest')

    return render(
        request,
        'board/my_quests.html',
        {'character_quests': character_quests}
    )




@login_required(login_url='/login/')
def complete_quest(request, quest_id):
    if request.method != 'POST':
        return redirect('my_quests')

    character = request.user.character

    character_quest = get_object_or_404(
        CharacterQuest,
        character=character,
        quest_id=quest_id,
    )

    # Нельзя получить награду повторно.
    if character_quest.is_completed:
        return redirect('my_quests')

    quest = character_quest.quest

    # Проверяем, выполнена ли цель.
    if character_quest.progress < quest.target_amount:
        return redirect('my_quests')

    # Выдаём награды.
    character.add_experience(quest.experience_reward)

    character.gold += quest.gold_reward
    character.save(update_fields=['gold'])

    character_quest.is_completed = True
    character_quest.save(update_fields=['is_completed'])

    return redirect('my_quests')




@login_required(login_url='/login/')
def battle_view(request, monster_id):
    character = request.user.character
    monster = get_object_or_404(Monster, id=monster_id)

    battle = Battle.objects.filter(
        character=character,
        monster=monster,
    ).order_by('-created_at').first()

    # Создаём первый бой, только если персонаж жив.
    if battle is None and character.health > 0:
        battle = Battle.objects.create(
            character=character,
            monster=monster,
            monster_health=monster.health,
        )

    return render(
        request,
        'board/battle.html',
        {
            'character': character,
            'monster': monster,
            'battle': battle,
        },
    )


@login_required(login_url='/login/')
def start_battle(request, monster_id):
    if request.method != 'POST':
        return redirect('battle', monster_id=monster_id)

    character = request.user.character
    monster = get_object_or_404(Monster, id=monster_id)

    # Мёртвый персонаж не может начать бой.
    if character.health <= 0:
        return redirect('character')

    latest_battle = Battle.objects.filter(
        character=character,
        monster=monster,
    ).order_by('-created_at').first()

    # Нельзя начать новый бой, пока предыдущий не завершён.
    if latest_battle and not latest_battle.is_finished:
        return redirect('battle', monster_id=monster_id)

    # Здоровье монстра берётся из его базовых характеристик.
    if monster.health <= 0:
        return redirect('my_quests')

    Battle.objects.create(
        character=character,
        monster=monster,
        monster_health=monster.health,
    )

    return redirect('battle', monster_id=monster_id)



@login_required(login_url='/login/')
def attack_monster(request, monster_id):
    if request.method != 'POST':
        return redirect('battle', monster_id=monster_id)

    character = request.user.character
    monster = get_object_or_404(Monster, id=monster_id)

    battle = Battle.objects.filter(
        character=character,
        monster=monster,
        is_finished=False,
    ).order_by('-created_at').first()

    if battle is None:
        return redirect('battle', monster_id=monster_id)

    if character.health <= 0:
        battle.is_finished = True
        battle.is_won = False
        battle.save(update_fields=['is_finished', 'is_won'])
        return redirect('battle', monster_id=monster_id)

    def finish_battle(won):
        battle.is_finished = True
        battle.is_won = won
        battle.save(update_fields=[
            'monster_health',
            'is_finished',
            'is_won',
        ])

    def character_attack():
        battle.monster_health = max(
            0,
            battle.monster_health - max(1, character.effective_strength),
        )
        return battle.monster_health == 0

    def monster_attack():
        character.health = max(
            0,
            character.health - max(
                1,
                monster.attack - character.effective_defense,
            ),
        )
        character.save(update_fields=['health'])
        return character.health == 0

    # Скорость определяет, кто атакует первым.
    if character.effective_speed > monster.speed:
        character_went_first = True
    else:
        character_went_first = False

    if character_went_first:
        # Сначала атакует персонаж.
        if character_attack():
            finish_battle(True)
        else:
            # Затем монстр.
            if monster_attack():
                finish_battle(False)
            else:
                battle.save(update_fields=['monster_health'])

    else:
        # Сначала атакует монстр.
        if monster_attack():
            finish_battle(False)
        else:
            # Затем персонаж.
            if character_attack():
                finish_battle(True)
            else:
                battle.save(update_fields=['monster_health'])

    # Если бой выигран, выдаём награды.
    if battle.is_finished and battle.is_won:
        character.add_experience(monster.experience_reward)

        character.gold += monster.gold_reward
        character.save(update_fields=['gold'])

        give_monster_drop(character, monster)

        character_quest = CharacterQuest.objects.filter(
            character=character,
            quest__monster=monster,
            is_completed=False,
            progress__lt=models.F('quest__target_amount'),
        ).first()

        if character_quest:
            character_quest.progress += 1
            character_quest.save(update_fields=['progress'])

    return redirect('battle', monster_id=monster_id)




@login_required(login_url = '/login/')
def heal_character(request):
    if request.method == 'POST':
        character = request.user.character

        character.health = character.max_health

        character.save(
            update_fields = ['health']
        )
    return redirect('character')


@login_required(login_url='/login/')
def restore_mana(request):
    if request.method == 'POST':
        character = request.user.character

        character.mana = character.max_mana

        character.save(
            update_fields = ['mana']
        )

    return redirect('character')



@login_required(login_url='/login/')
def increase_strength(request):
    if request.method == 'POST':
        character = request.user.character

        if character.stat_points > 0:
            character.strength += 1
            character.stat_points -= 1
            character.save(update_fields=[
                'strength',
                'stat_points',
            ])

    return redirect('character')


@login_required(login_url='/login/')
def increase_defense(request):
    if request.method == 'POST':
        character = request.user.character

        if character.stat_points > 0:
            character.defense += 1
            character.stat_points -= 1
            character.save(update_fields=[
                'defense',
                'stat_points',
            ])

    return redirect('character')


@login_required(login_url='/login/')
def increase_speed(request):
    if request.method == 'POST':
        character = request.user.character

        if character.stat_points > 0:
            character.speed += 1
            character.stat_points -= 1
            character.save(update_fields=[
                'speed',
                'stat_points',
            ])

    return redirect('character')



@login_required(login_url='/login/')
def inventory_view(request):
    character = request.user.character

    inventory_items = CharacterInventory.objects.filter(
        character=character,
    ).select_related('item').order_by('item__name')

    return render(
        request,
        'board/inventory.html',
        {
            'character': character,
            'inventory_items': inventory_items,
        },
    )


@login_required(login_url='/login/')
def equip_item(request, inventory_id):
    if request.method != 'POST':
        return redirect('inventory')

    character = request.user.character

    inventory_entry = get_object_or_404(
        CharacterInventory,
        id=inventory_id,
        character=character,
    )

    item = inventory_entry.item

    if item.item_type not in ('weapon', 'armor'):
        return redirect('inventory')

    if inventory_entry.quantity < 1:
        return redirect('inventory')

    # Снимаем предыдущий предмет того же типа.
    for entry in CharacterInventory.objects.filter(
        character=character,
        is_equipped=True,
        item__item_type=item.item_type,
    ).exclude(id=inventory_entry.id):
        entry.is_equipped = False
        entry.save(update_fields=['is_equipped'])

    inventory_entry.is_equipped = True
    inventory_entry.save(update_fields=['is_equipped'])

    return redirect('inventory')


@login_required(login_url='/login/')
def unequip_item(request, inventory_id):
    if request.method != 'POST':
        return redirect('inventory')

    inventory_entry = get_object_or_404(
        CharacterInventory,
        id=inventory_id,
        character=request.user.character,
    )

    inventory_entry.is_equipped = False
    inventory_entry.save(update_fields=['is_equipped'])

    return redirect('inventory')


@login_required(login_url='/login/')
def use_item(request, inventory_id):
    if request.method != 'POST':
        return redirect('inventory')

    character = request.user.character

    inventory_entry = get_object_or_404(
        CharacterInventory,
        id=inventory_id,
        character=character,
    )

    item = inventory_entry.item

    # Использовать можно только зелья.
    if item.item_type != 'potion':
        return redirect('inventory')

    if inventory_entry.quantity < 1:
        return redirect('inventory')

    # Не тратим зелье, если здоровье уже полное.
    if character.health >= character.max_health:
        return redirect('inventory')

    if item.heal_amount <= 0:
        return redirect('inventory')

    character.health = min(
        character.max_health,
        character.health + item.heal_amount,
    )
    character.save(update_fields=['health'])

    inventory_entry.quantity -= 1

    if inventory_entry.quantity == 0:
        inventory_entry.delete()
    else:
        inventory_entry.save(update_fields=['quantity'])

    return redirect('inventory')




def give_monster_drop(character, monster):
    items = Item.objects.filter(drop_chance__gt=0)

    for item in items:
        if random.randint(1, 100) <= item.drop_chance:
            inventory_entry, created = CharacterInventory.objects.get_or_create(
                character=character,
                item=item,
                defaults={'quantity': item.drop_quantity},
            )

            if not created:
                inventory_entry.quantity += item.drop_quantity
                inventory_entry.save(update_fields=['quantity'])