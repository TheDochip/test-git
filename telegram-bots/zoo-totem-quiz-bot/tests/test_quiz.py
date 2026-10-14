import itertools
import random
import sys
from collections import Counter
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quiz import QuizSession, format_result, progress_bar, validate_data  # noqa: E402
from quiz_data import ANIMALS, QUESTIONS  # noqa: E402

TOY_QUESTIONS = [
    {"id": 1, "text": "q1", "answers": [{"text": "a", "weights": {"лев": 3, "волк": 1}},
                                        {"text": "b", "weights": {"сова": 3}}]},
    {"id": 2, "text": "q2", "answers": [{"text": "a", "weights": {"лев": 2}},
                                        {"text": "b", "weights": {"волк": 3}}]},
]


class DataTests(unittest.TestCase):
    def test_real_data_is_consistent(self):
        validate_data()
        self.assertEqual(len(QUESTIONS), 8)

    def test_every_animal_can_win(self):
        reachable = {a for q in QUESTIONS for ans in q["answers"] for a, w in ans["weights"].items() if w == 3}
        self.assertEqual(reachable, set(ANIMALS))

    def test_results_are_balanced(self):
        """Перебираем все 4^8 вариантов ответов: каждое животное должно выпадать в 3–8% случаев."""
        wins = Counter()
        for combo in itertools.product(range(4), repeat=len(QUESTIONS)):
            scores = Counter()
            for question, i in zip(QUESTIONS, combo):
                scores.update(question["answers"][i]["weights"])
            best = max(scores.values())
            leaders = [a for a, s in scores.items() if s == best]
            for animal in leaders:
                wins[animal] += 1 / len(leaders)
        total = 4 ** len(QUESTIONS)
        for animal in ANIMALS:
            share = wins[animal] / total * 100
            self.assertTrue(3 <= share <= 8, f"{animal}: {share:.2f}%")

    def test_unknown_animal_detected(self):
        bad = [{"id": 1, "text": "", "answers": [{"text": "", "weights": {"единорог": 3}}]}]
        with self.assertRaises(ValueError):
            validate_data(ANIMALS, bad)


class SessionTests(unittest.TestCase):
    def test_full_run(self):
        s = QuizSession(questions=TOY_QUESTIONS)
        s.answer(0)
        self.assertFalse(s.finished)
        s.answer(0)
        self.assertTrue(s.finished)
        r = s.result()
        self.assertEqual(r.winner, "лев")
        # лев может набрать максимум 3 + 2 = 5 и набрал все 5
        self.assertEqual((r.score, r.max_score, r.percentage), (5, 5, 100))
        self.assertEqual(r.runners_up, ["волк"])

    def test_tie_is_resolved_by_rng(self):
        s = QuizSession(questions=TOY_QUESTIONS)
        s.answer(1)  # сова 3
        s.answer(1)  # волк 3
        winners = {s.result(random.Random(seed)).winner for seed in range(20)}
        self.assertEqual(winners, {"сова", "волк"})

    def test_cannot_answer_after_finish_or_with_bad_index(self):
        s = QuizSession(questions=TOY_QUESTIONS)
        with self.assertRaises(IndexError):
            s.answer(5)
        s.answer(0)
        s.answer(0)
        with self.assertRaises(RuntimeError):
            s.answer(0)

    def test_result_before_finish(self):
        with self.assertRaises(RuntimeError):
            QuizSession(questions=TOY_QUESTIONS).result()

    def test_real_quiz_always_produces_result(self):
        rng = random.Random(1)
        for _ in range(200):
            s = QuizSession()
            while not s.finished:
                s.answer(rng.randrange(len(s.question["answers"])))
            r = s.result(rng)
            self.assertIn(r.winner, ANIMALS)
            self.assertLessEqual(r.percentage, 100)


class FormatTests(unittest.TestCase):
    def test_progress_bar(self):
        self.assertEqual(progress_bar(4, 8), "█████░░░░░ 4/8")

    def test_format_result_mentions_animal(self):
        s = QuizSession(questions=TOY_QUESTIONS)
        s.answer(0)
        s.answer(0)
        text = format_result(s.result(), "Никита")
        self.assertIn("Лев", text)
        self.assertIn("Никита", text)


if __name__ == "__main__":
    unittest.main()
