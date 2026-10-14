import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logic import (  # noqa: E402
    InputError,
    NewExpense,
    format_report,
    limit_status,
    money,
    parse_add,
    parse_limit,
    period,
)


class ParseAddTests(unittest.TestCase):
    def test_full_command(self):
        self.assertEqual(parse_add("/add 500 еда обед в кафе"),
                         NewExpense(Decimal("500.00"), "Еда", "обед в кафе"))

    def test_without_description_and_with_comma(self):
        self.assertEqual(parse_add("/add 99,9 Транспорт"), NewExpense(Decimal("99.90"), "Транспорт", None))

    def test_too_short(self):
        with self.assertRaises(InputError):
            parse_add("/add 500")

    def test_bad_amounts(self):
        for amount in ("abc", "0", "-10", "nan", "inf", "99999999999"):
            with self.subTest(amount=amount), self.assertRaises(InputError):
                parse_add(f"/add {amount} Еда")


class ParseLimitTests(unittest.TestCase):
    def test_show_current(self):
        self.assertIsNone(parse_limit("/limit"))

    def test_set_and_reset(self):
        self.assertEqual(parse_limit("/limit 30000"), Decimal("30000.00"))
        self.assertEqual(parse_limit("/limit 0"), Decimal("0.00"))

    def test_invalid(self):
        for raw in ("/limit -5", "/limit много"):
            with self.subTest(raw=raw), self.assertRaises(InputError):
                parse_limit(raw)


class PeriodTests(unittest.TestCase):
    def test_periods(self):
        today = date(2026, 10, 13)
        self.assertEqual(period("today", today)[:2], (today, today))
        self.assertEqual(period("week", today)[:2], (date(2026, 10, 7), today))
        self.assertEqual(period("month", today)[:2], (date(2026, 10, 1), today))
        with self.assertRaises(ValueError):
            period("year", today)


class FormatTests(unittest.TestCase):
    def test_money(self):
        self.assertEqual(money(Decimal("12345.5")), "12 345,50 ₽")

    def test_limit_status(self):
        self.assertEqual(limit_status(Decimal(100), Decimal(0)), "")
        self.assertIn("использовано 25%", limit_status(Decimal(250), Decimal(1000)))
        self.assertIn("превышен на 50,00 ₽", limit_status(Decimal(1050), Decimal(1000)))

    def test_empty_report(self):
        self.assertIn("расходов нет", format_report("сегодня", [], Decimal(0), []))

    def test_report(self):
        rows = [
            {"expense_date": date(2026, 10, 13), "amount": Decimal(300), "category_name": "Еда", "description": "обед"},
            {"expense_date": date(2026, 10, 12), "amount": Decimal(100), "category_name": None, "description": None},
        ]
        by_cat = [{"category_name": "Еда", "total": Decimal(300)}, {"category_name": None, "total": Decimal(100)}]
        text = format_report("неделю", rows, Decimal(400), by_cat)
        self.assertIn("13.10 · 300,00 ₽ · Еда — обед", text)
        self.assertIn("Без категории: 100,00 ₽ (25%)", text)
        self.assertIn("Итого: 400,00 ₽", text)


if __name__ == "__main__":
    unittest.main()
