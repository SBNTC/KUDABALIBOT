"""
Тесты логики дедупликации — _normalize и алгоритм fuzzy matching.

Тестируем только чистую логику без БД (AsyncSessionMaker не используется).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from difflib import SequenceMatcher
from services.dedup import _normalize, FUZZY_THRESHOLD, FUZZY_PREFIX


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercases(self):
        assert _normalize("ЙОГА НА БАЛИ") == "йога на бали"

    def test_collapses_whitespace(self):
        assert _normalize("йога  \t на   бали") == "йога на бали"

    def test_truncates_to_fuzzy_prefix(self):
        long = "а" * (FUZZY_PREFIX + 50)
        result = _normalize(long)
        assert len(result) == FUZZY_PREFIX

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_none_returns_empty(self):
        assert _normalize(None) == ""

    def test_strips_leading_trailing(self):
        assert _normalize("  привет  ") == "привет"


# ---------------------------------------------------------------------------
# Fuzzy similarity algorithm (extracted logic, no DB)
# ---------------------------------------------------------------------------

def _would_be_duplicate(candidate: str, kept_norms: list[str], threshold: float = FUZZY_THRESHOLD) -> bool:
    """Воспроизводит логику fuzzy_dedup без БД."""
    norm = _normalize(candidate)
    for kept_norm in kept_norms:
        if SequenceMatcher(None, norm, kept_norm).ratio() >= threshold:
            return True
    return False


class TestFuzzyLogic:
    def test_identical_texts_are_duplicates(self):
        text = "Открытая йога каждое утро у пляжа Берава, вход свободный"
        assert _would_be_duplicate(text, [text]) is True

    def test_slightly_different_texts_are_duplicates(self):
        original = "Открытая йога каждое утро у пляжа Берава, вход свободный, приходите!"
        variant  = "Открытая йога каждое утро у пляжа Берава, вход свободный. Ждём вас!"
        assert _would_be_duplicate(variant, [original]) is True

    def test_completely_different_texts_are_not_duplicates(self):
        a = "Концерт живой музыки в пятницу вечером у океана"
        b = "Воркшоп по акварели для начинающих художников в Убуде"
        assert _would_be_duplicate(a, [b]) is False

    def test_empty_kept_list(self):
        assert _would_be_duplicate("любой текст", []) is False

    def test_threshold_boundary(self):
        # Два совершенно разных текста одинаковой длины — ratio должен быть << 0.80
        a = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        b = "яюэьыъщшчцхфутсрпонмлкйизжёедгвба"  # реверс
        ratio = SequenceMatcher(None, a, b).ratio()
        assert ratio < FUZZY_THRESHOLD

    def test_first_kept_wins(self):
        # fuzzy_dedup keeps the FIRST seen (oldest), later duplicates are removed
        original = "Нетворкинг для предпринимателей каждую среду в кафе Ubud"
        duplicate = "Нетворкинг для предпринимателей каждую среду в кафе Ubud!!!"

        kept: list[tuple[int, str]] = []
        to_delete: list[int] = []

        items = [(1, original), (2, duplicate)]
        for item_id, text in items:
            norm = _normalize(text)
            is_dup = any(
                SequenceMatcher(None, norm, k).ratio() >= FUZZY_THRESHOLD
                for k in [kn for _, kn in kept]
            )
            if is_dup:
                to_delete.append(item_id)
            else:
                kept.append((item_id, norm))

        assert to_delete == [2]  # duplicate removed, original kept
        assert [kid for kid, _ in kept] == [1]
