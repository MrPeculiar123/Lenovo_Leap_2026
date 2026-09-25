"""Safe normalization and comparison for assessment answers."""

import re
from typing import Iterable


_OPTION_PREFIX = re.compile(r"^\s*([A-Da-d])\s*[).:\-]\s*")


def normalize_answer(value: object) -> str:
    """Normalize text without executing or interpreting learner-provided code."""
    return " ".join(str(value or "").strip().casefold().split())


def _without_option_prefix(value: object) -> str:
    text = str(value or "").strip()
    match = _OPTION_PREFIX.match(text)
    return text[match.end():].strip() if match else text


def evaluate_answer(student_answer: object, correct_answer: object, options: Iterable[str] | None = None) -> bool:
    """Compare letters, prefixed options, and exact text answers safely."""
    student = str(student_answer or "").strip()
    correct = str(correct_answer or "").strip()
    if not student or not correct:
        return False

    student_letter = student[:1].casefold() if len(student) == 1 and student.casefold() in "abcd" else None
    correct_match = _OPTION_PREFIX.match(correct)
    correct_letter = correct_match.group(1).casefold() if correct_match else None
    if student_letter and correct_letter:
        return student_letter == correct_letter

    normalized_student = normalize_answer(_without_option_prefix(student))
    normalized_correct = normalize_answer(_without_option_prefix(correct))
    if normalized_student == normalized_correct:
        return True

    # Accept a letter against a prefixed option, including generated option text.
    if student_letter and options:
        index = ord(student_letter) - ord("a")
        option_list = list(options)
        if 0 <= index < len(option_list):
            return normalize_answer(_without_option_prefix(option_list[index])) == normalized_correct

    return False
