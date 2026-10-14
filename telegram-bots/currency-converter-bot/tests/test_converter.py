import sys
import unittest
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from converter import (  # noqa: E402
    ConversionError,
    ConversionRequest,
    RateProvider,
    format_amount,
    format_result,
    parse_request,
)
from currencies import resolve_currency  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeHttp:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def __call__(self, url, timeout):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


OK_PAYLOAD = {"result": "success", "rates": {"USD": 1.0, "RUB": 90.5, "EUR": 0.92}}


class ParseRequestTests(unittest.TestCase):
    def test_words_and_codes(self):
        self.assertEqual(parse_request("доллар рубль 100"), ConversionRequest("USD", "RUB", 100.0))
        self.assertEqual(parse_request("eur Usd 2,5"), ConversionRequest("EUR", "USD", 2.5))

    def test_wrong_number_of_params(self):
        for text in ("доллар рубль", "доллар рубль 1 2", ""):
            with self.assertRaises(ConversionError):
                parse_request(text)

    def test_unknown_currency(self):
        with self.assertRaisesRegex(ConversionError, "тугрик"):
            parse_request("тугрик рубль 1")

    def test_same_currency(self):
        with self.assertRaises(ConversionError):
            parse_request("usd доллар 1")

    def test_bad_amount(self):
        for amount in ("abc", "0", "-5"):
            with self.assertRaises(ConversionError):
                parse_request(f"usd rub {amount}")

    def test_resolve_is_case_insensitive(self):
        self.assertEqual(resolve_currency("  РУБЛЬ "), "RUB")
        self.assertIsNone(resolve_currency("abc"))


class RateProviderTests(unittest.TestCase):
    def test_convert(self):
        provider = RateProvider(http_get=FakeHttp(FakeResponse(OK_PAYLOAD)))
        result = provider.convert(ConversionRequest("USD", "RUB", 10))
        self.assertAlmostEqual(result.total, 905.0)

    def test_cache_is_used_within_ttl(self):
        http = FakeHttp(FakeResponse(OK_PAYLOAD))
        now = [0.0]
        provider = RateProvider(http_get=http, clock=lambda: now[0])
        provider.get_rate("USD", "RUB")
        now[0] = 100
        provider.get_rate("USD", "EUR")
        self.assertEqual(http.calls, 1)
        now[0] = 10_000
        provider.get_rate("USD", "EUR")
        self.assertEqual(http.calls, 2)

    def test_network_error_is_user_friendly(self):
        provider = RateProvider(http_get=FakeHttp(requests.ConnectionError("boom")))
        with self.assertRaisesRegex(ConversionError, "недоступен"):
            provider.get_rate("USD", "RUB")

    def test_http_error(self):
        provider = RateProvider(http_get=FakeHttp(FakeResponse({}, status=500)))
        with self.assertRaises(ConversionError):
            provider.get_rate("USD", "RUB")

    def test_bad_payload(self):
        provider = RateProvider(http_get=FakeHttp(FakeResponse({"result": "error"})))
        with self.assertRaises(ConversionError):
            provider.get_rate("USD", "RUB")

    def test_missing_target(self):
        provider = RateProvider(http_get=FakeHttp(FakeResponse(OK_PAYLOAD)))
        with self.assertRaises(ConversionError):
            provider.get_rate("USD", "KZT")


class FormatTests(unittest.TestCase):
    def test_format_amount(self):
        self.assertEqual(format_amount(1234567.891), "1 234 567,89")

    def test_format_result(self):
        provider = RateProvider(http_get=FakeHttp(FakeResponse(OK_PAYLOAD)))
        text = format_result(provider.convert(ConversionRequest("USD", "RUB", 2)))
        self.assertIn("181,00 RUB", text)
        self.assertIn("1 USD = 90.5000 RUB", text)


if __name__ == "__main__":
    unittest.main()
