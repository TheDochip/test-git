"""Логика викторины без привязки к Telegram: сессия, подсчёт баллов, результат."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

from quiz_data import ANIMALS, QUESTIONS

MAX_WEIGHT = 3  # максимальный вес ответа для одного животного
PROGRESS_BAR_LENGTH = 10


def validate_data(animals: dict = ANIMALS, questions: list = QUESTIONS) -> None:
    """Проверяет, что веса ссылаются только на существующих животных."""
    for question in questions:
        for answer in question["answers"]:
            unknown = set(answer["weights"]) - set(animals)
            if unknown:
                raise ValueError(f"Вопрос {question['id']}: неизвестные животные {sorted(unknown)}")
            if max(answer["weights"].values()) > MAX_WEIGHT:
                raise ValueError(f"Вопрос {question['id']}: вес больше {MAX_WEIGHT}")


def max_score_for(animal: str, questions: list = QUESTIONS) -> int:
    """Максимум баллов, который животное может набрать, если на все вопросы ответить «в его пользу»."""
    return sum(max(a["weights"].get(animal, 0) for a in q["answers"]) for q in questions)


@dataclass
class QuizResult:
    winner: str
    percentage: int
    score: int
    max_score: int
    runners_up: list[str]  # следующие животные по количеству баллов


@dataclass
class QuizSession:
    questions: list = field(default_factory=lambda: QUESTIONS)
    current: int = 0
    scores: Counter = field(default_factory=Counter)

    @property
    def finished(self) -> bool:
        return self.current >= len(self.questions)

    @property
    def question(self) -> dict:
        return self.questions[self.current]

    def answer(self, answer_index: int) -> None:
        if self.finished:
            raise RuntimeError("Викторина уже завершена")
        answers = self.question["answers"]
        if not 0 <= answer_index < len(answers):
            raise IndexError("Нет такого варианта ответа")
        self.scores.update(answers[answer_index]["weights"])
        self.current += 1

    def result(self, rng: random.Random | None = None) -> QuizResult:
        if not self.finished:
            raise RuntimeError("Викторина ещё не завершена")
        rng = rng or random.Random()
        best = max(self.scores.values())
        # При равенстве баллов выбираем случайно, чтобы результат не был всегда одинаковым
        winner = rng.choice(sorted(a for a, s in self.scores.items() if s == best))
        # Процент совпадения считаем от максимума, который может набрать именно это животное
        max_score = max_score_for(winner, self.questions)
        return QuizResult(
            winner=winner,
            percentage=round(best / max_score * 100),
            score=best,
            max_score=max_score,
            runners_up=[a for a, _ in self.scores.most_common() if a != winner][:3],
        )


def progress_bar(current: int, total: int, length: int = PROGRESS_BAR_LENGTH) -> str:
    filled = int(length * current / total)
    return "█" * filled + "░" * (length - filled) + f" {current}/{total}"


def format_result(result: QuizResult, username: str) -> str:
    animal = ANIMALS[result.winner]
    text = (
        f"🎉 <b>{username}, ваше тотемное животное — {animal['emoji']} {animal['name']}!</b>\n"
        f"Совпадение: {result.percentage}% ({result.score} из {result.max_score} возможных баллов)\n\n"
        f"📖 {animal['description']}\n\n"
        f"🐾 <b>Факт из Московского зоопарка:</b>\n{animal['fact']}\n\n"
        f"💝 <b>Программа опеки:</b>\n{animal['opeka_text']}"
    )
    if result.runners_up:
        close = ", ".join(f"{ANIMALS[key]['emoji']} {ANIMALS[key]['name']}" for key in result.runners_up)
        text += f"\n\n📊 <b>Вам также близки:</b> {close}"
    return text
