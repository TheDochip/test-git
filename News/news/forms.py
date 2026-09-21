from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import RegexValidator

from .models import Category, Comment, Post, Profile, User
from .validators import validate_image_upload


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password_confirm = forms.CharField(
        label='Повторите пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ('username',)
        labels = {'username': 'Имя пользователя'}

    def clean_username(self):
        username = self.cleaned_data['username']
        # Стандартная проверка уникальности регистрозависимая: Ivan и ivan прошли бы оба.
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Пользователь с таким именем уже существует.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Пароли не совпадают.')
            return cleaned_data

        if password:
            # Без этого вызова валидаторы из AUTH_PASSWORD_VALIDATORS не срабатывают.
            candidate = User(username=cleaned_data.get('username', ''))
            try:
                password_validation.validate_password(password, user=candidate)
            except ValidationError as error:
                self.add_error('password', error)

        return cleaned_data


class AddEmailForm(forms.Form):
    email = forms.EmailField(label='Email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Этот email уже привязан к другому аккаунту.')
        return email


class ActivationCodeForm(forms.Form):
    code = forms.CharField(
        label='Код подтверждения',
        min_length=6,
        max_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'Код состоит из 6 цифр.')],
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}),
    )


class CommentForm(forms.ModelForm):
    content = forms.CharField(
        label='Комментарий',
        max_length=3000,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Напишите комментарий...'}),
    )

    class Meta:
        model = Comment
        fields = ('content',)


class SubscriptionForm(forms.Form):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Категории',
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('avatar', 'bio', 'show_subscriptions')
        labels = {
            'avatar': 'Аватар',
            'bio': 'О себе',
            'show_subscriptions': 'Показывать мои подписки другим',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if isinstance(avatar, UploadedFile):
            validate_image_upload(avatar)
        return avatar


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'category', 'cover')
        labels = {
            'title': 'Название',
            'category': 'Категория',
            'cover': 'Обложка',
        }
        widgets = {'cover': forms.ClearableFileInput(attrs={'accept': 'image/*'})}

    def clean_cover(self):
        cover = self.cleaned_data.get('cover')
        if isinstance(cover, UploadedFile):
            validate_image_upload(cover)
        return cover
