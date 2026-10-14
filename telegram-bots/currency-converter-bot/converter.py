"""Бизнес-логика конвертера: разбор запроса пользователя и получение курса.

Модуль не зависит от Telegram, поэтому его легко тестировать отдельно от бота.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import requests

from currencies import CURRENCIES, resolve_currency

API_URL = "https://open.er-api.com/v6/latest/{base}"
CACHE_TTL_SECONDS = 600  # курсы обновляются раз в сутки, 10 минут кеша более чем достаточно
REQUEST_TIMEOUT_SECONDS = 10


class ConversionError(Exception):
    """Ошибка, которую можно показать пользователю как есть."""


@dataclass(frozen=True)
class ConversionRequest:
    source: str  # ISO-код исходной валюты, например USD
    target: str  # ISO-код валюты, в которую переводим
    amount: float


@dataclass(frozen=True)
class ConversionResult:
    request: ConversionRequest
    rate: float

    @property
    def total(self) -> float:
        return self.request.amount * self.rate


def parse_request(text: str) -> ConversionRequest:
    """Разбирает строку вида «доллар рубль 100» или «USD RUB 100,5»."""
    parts = text.split()
    if len(parts) != 3:
        raise ConversionError(
            "Нужно три параметра: <валюта> <в какую валюту> <количество>.\n"
            "Пример: доллар рубль 100"
        )

    source_raw, target_raw, amount_raw = parts
    source = resolve_currency(source_raw)
    if source is None:
        raise ConversionError(f"Не знаю валюту «{source_raw}». Список: /values")
    target = resolve_currency(target_raw)
    if target is None:
        raise ConversionError(f"Не знаю валюту «{target_raw}». Список: /values")
    if source == target:
        raise ConversionError("Валюты совпадают — переводить нечего.")

    try:
        amount = float(amount_raw.replace(",", "."))
    except ValueError:
        raise ConversionError(f"«{amount_raw}» не похоже на число.") from None
    if amount <= 0:
        raise ConversionError("Количество должно быть больше нуля.")

    return ConversionRequest(source, target, amount)


class RateProvider:
    """Получает курсы из открытого API (без ключа) и кеширует ответ по базовой валюте."""

    def __init__(
        self,
        http_get: Callable[..., requests.Response] = requests.get,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http_get = http_get
        self._clock = clock
        self._cache: dict[str, tuple[float, dict[str, float]]] = {}

    def _rates_for(self, base: str) -> dict[str, float]:
        cached = self._cache.get(base)
        if cached and self._clock() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

        try:
            response = self._http_get(API_URL.format(base=base), timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            raise ConversionError("Сервис курсов сейчас недоступен, попробуйте позже.") from None

        if data.get("result") != "success" or "rates" not in data:
            raise ConversionError("Сервис курсов вернул некорректный ответ.")

        rates = data["rates"]
        self._cache[base] = (self._clock(), rates)
        return rates

    def get_rate(self, source: str, target: str) -> float:
        rates = self._rates_for(source)
        if target not in rates:
            raise ConversionError(f"Нет курса {source} → {target}.")
        return float(rates[target])

    def convert(self, request: ConversionRequest) -> ConversionResult:
        return ConversionResult(request, self.get_rate(request.source, request.target))


def format_amount(value: float) -> str:
    """1234567.891 -> «1 234 567,89»"""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def format_result(result: ConversionResult) -> str:
    req = result.request
    src_name = CURRENCIES[req.source][0]
    dst_name = CURRENCIES[req.target][0]
    return (
        f"{format_amount(req.amount)} {req.source} ({src_name}) = "
        f"{format_amount(result.total)} {req.target} ({dst_name})\n"
        f"Курс: 1 {req.source} = {result.rate:.4f} {req.target}"
    )
