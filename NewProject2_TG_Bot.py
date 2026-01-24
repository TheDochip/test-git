import telebot
import requests
import json



TOKEN = '8021511271:AAGRkOqZ-r8OrQdi5jy0yfUETRDmc52eJFs'
bot = telebot.TeleBot(TOKEN)
keys = {
    # Основные валюты
    'рубль': 'RUB',
    'евро': 'EUR',
    'доллар': 'USD',
    'фунт': 'GBP',
    'иена': 'JPY',
    'юань': 'CNY',
    'франк': 'CHF',

    # Другие популярные валюты
    'злотый': 'PLN',
    'крона': 'CZK',  # чешская
    'кронаш': 'SEK',  # шведская
    'кронан': 'NOK',  # норвежская
    'лира': 'TRY',  # турецкая
    'вона': 'KRW',  # корейская
    'дирхам': 'AED',  # ОАЭ
    'шекель': 'ILS',  # израильский

    # Азиатские валюты
    'рупия': 'INR',  # индийская
    'рупияи': 'IDR',  # индонезийская
    'бат': 'THB',  # тайский
    'песо': 'PHP',  # филиппинский

    # Европейские (не евро)
    'лей': 'RON',  # румынский
    'лев': 'BGN',  # болгарский
    'форинт': 'HUF',  # венгерский
}


class ConvertionException(Exception):
    pass

class CryptoConvertion:
    @staticmethod
    def convert(quote: str, base: str, amount: str):
        if quote == base:
            raise ConvertionException(f'Невозможно перевести одинаковые валюты')

        try:
            quote_ticker = keys[quote]
        except KeyError:
            raise ConvertionException(f'Не удалось обработать валюту {quote}')

        try:
            base_ticker = keys[base]
        except KeyError:
            raise ConvertionException(f'Не удалось обработать валюту {base}')

        try:
            amount = float(amount)
        except ValueError:
            raise ConvertionException(f'Не удалось обработать количество {amount}')

        r = requests.get(f'https://v6.exchangerate-api.com/v6/90b40de1bf54049b2563292a/latest/{quote_ticker}')
        data = r.json()
        total_base = data['conversion_rates'][f'{base_ticker}']

        return total_base



@bot.message_handler(commands=['start', 'help'])
def help(message: telebot.types.Message):
    text = '<имя валюты, цену которой он хочет узнать>\
         <имя валюты, в которой надо узнать цену первой валюты>\
          <количество первой валюты>\n Увидеть список всех доступных валют /values'
    bot.reply_to(message, text)

@bot.message_handler(commands=['values'])
def values(masseg: telebot.types.Message):
    text = 'Доступные валюты:'
    for key in keys.keys():
        text = '\n'.join((text, key,))
    bot.reply_to(masseg, text)

@bot.message_handler(content_types=['text'])
def convert(message: telebot.types.Message):
    try:
        values = message.text.split(' ')

        if len(values) != 3:
            raise ConvertionException(f'Слишком много параметров')

        quote, base, amount = values
        total_base = CryptoConvertion.convert(quote, base, amount)
    except ConvertionException as e:
        bot.reply_to(message, f'Ошибка пользователя.\n{e}')
    except Exception as e:
        bot.reply_to(message, f'Не удалось обработать команду\n{e}')
    else:
        text = f'Цена {amount} {quote} в {base} - {float(total_base) * float(amount)}'
        bot.send_message(message.chat.id, text)

bot.polling()