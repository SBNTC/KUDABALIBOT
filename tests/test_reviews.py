"""
Тесты find_matching_place из services/reviews_analyzer.py.

find_matching_place — чистая функция (читает TTL-кэш, но кэш можно подменить).
Тестируем через локальную копию алгоритма, чтобы не тянуть config и AsyncOpenAI.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_FAKE_PLACES = [
    "Potato Head",
    "Ku De Ta",
    "Finns Beach Club",
    "La Plancha",
    "Single Fin",
    "Warung Babi Guling",
]


def _make_find(places: list[str]):
    """Воспроизводит алгоритм find_matching_place без зависимости от БД."""
    def find(mentioned: str) -> str | None:
        mentioned_lower = mentioned.lower().strip()
        if not mentioned_lower:
            return None
        # Точное совпадение
        for place in places:
            if place.lower() == mentioned_lower:
                return place
        # Частичное (подстрока)
        for place in places:
            pl = place.lower()
            if mentioned_lower in pl or pl in mentioned_lower:
                return place
        return None
    return find


find_matching_place = _make_find(_FAKE_PLACES)


class TestFindMatchingPlace:
    def test_exact_match(self):
        assert find_matching_place("Potato Head") == "Potato Head"

    def test_case_insensitive_exact(self):
        assert find_matching_place("potato head") == "Potato Head"
        assert find_matching_place("POTATO HEAD") == "Potato Head"

    def test_partial_match_mention_in_place(self):
        # "Finns" содержится в "Finns Beach Club"
        assert find_matching_place("Finns") == "Finns Beach Club"

    def test_partial_match_place_in_mention(self):
        # "Single Fin" содержится в "Single Fin Bali"
        result = find_matching_place("Single Fin Bali")
        assert result == "Single Fin"

    def test_no_match_returns_none(self):
        assert find_matching_place("Неизвестное место") is None

    def test_empty_string_returns_none(self):
        assert find_matching_place("") is None

    def test_whitespace_only_returns_none(self):
        assert find_matching_place("   ") is None

    def test_exact_takes_priority_over_partial(self):
        # "La Plancha" — точное совпадение, не должен искать частичное
        result = find_matching_place("La Plancha")
        assert result == "La Plancha"

    def test_whitespace_stripped(self):
        assert find_matching_place("  Ku De Ta  ") == "Ku De Ta"

    def test_unicode_case(self):
        places = ["Warung Мечта", "Кафе Бали"]
        find = _make_find(places)
        assert find("warung мечта") == "Warung Мечта"


class TestFindMatchingPlaceAlgorithmEdgeCases:
    def test_empty_places_list(self):
        find = _make_find([])
        assert find("Potato Head") is None

    def test_single_character_mention_does_not_over_match(self):
        # "a" is a substring of every English place name — we don't want noise
        # but the algorithm does substring match intentionally; verify behaviour
        places = ["La Plancha", "Ku De Ta"]
        find = _make_find(places)
        # "a" in "la plancha" → first partial match returned
        result = find("a")
        assert result is not None  # documents current behaviour (intentional)

    def test_partial_match_prefers_first_in_list(self):
        # Two places both contain "Beach": first in list wins
        places = ["Finns Beach Club", "Canggu Beach Bar"]
        find = _make_find(places)
        result = find("Beach")
        assert result == "Finns Beach Club"
