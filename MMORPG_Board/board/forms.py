from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Post, Reply
from .sanitizer import sanitize_html

User = get_user_model()

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
    )
    password_confirm = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm')
        labels = {
            'username': 'Имя пользователя',
            'email': 'E-mail',
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Этот e-mail уже зарегистрирован.')

        return email

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Пароли не совпадают.')
        elif password:
            try:
                validate_password(
                    password,
                    User(
                        username=cleaned_data.get('username', ''),
                        email=cleaned_data.get('email', ''),
                    ),
                )
            except forms.ValidationError as error:
                self.add_error('password', error)

        return cleaned_data


class EmailVerificationForm(forms.Form):
    code = forms.CharField(
        label='Код подтверждения',
        max_length=6,
        min_length=6
    )


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя',
    )

    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
    )


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'category', 'content')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Например: Ищу хила в рейд'}),
            # Поле превращается в визуальный редактор (TinyMCE) в шаблоне
            'content': forms.Textarea(attrs={'class': 'rich-editor', 'rows': 15}),
        }

    def clean_content(self):
        content = sanitize_html(self.cleaned_data['content'])
        # Пустой текст: в редакторе может остаться только "<p></p>"
        has_media = '<img' in content or '<iframe' in content
        if not has_media and not strip_tags_text(content):
            raise forms.ValidationError('Напишите текст объявления.')
        return content


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ('text',)
        labels = {'text': 'Ваш отклик'}
        widgets = {
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Напишите автору объявления…'}),
        }


def strip_tags_text(html):
    from django.utils.html import strip_tags

    return strip_tags(html).replace('&nbsp;', ' ').strip()
