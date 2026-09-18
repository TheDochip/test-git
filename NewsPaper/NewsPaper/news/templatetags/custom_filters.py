from django import template

register = template.Library()

@register.filter()
def censor(value):
    forbidden_words = ['редиска', 'дурак', 'ерунда', 'плохое слово']
    for word in forbidden_words:
        value = value.replace(word, '*' * len(word))
    return value