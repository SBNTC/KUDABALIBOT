"""
Тесты compute_text_hash из database/models.py.

Чистая функция — не требует БД.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.models import compute_text_hash


class TestComputeTextHash:
    def test_deterministic(self):
        assert compute_text_hash("Привет Бали!") == compute_text_hash("Привет Бали!")

    def test_case_insensitive(self):
        # нормализация к lower
        assert compute_text_hash("ЙОГА") == compute_text_hash("йога")

    def test_strips_whitespace(self):
        assert compute_text_hash("  текст  ") == compute_text_hash("текст")

    def test_different_texts_differ(self):
        assert compute_text_hash("событие А") != compute_text_hash("событие Б")

    def test_returns_hex_string(self):
        result = compute_text_hash("test")
        assert isinstance(result, str)
        assert len(result) == 64  # sha256 hex
        int(result, 16)  # must be valid hex — raises ValueError if not

    def test_truncates_at_500(self):
        # Тексты, отличающиеся только после 500 символов, дают одинаковый хэш
        base = "а" * 500
        assert compute_text_hash(base + "X") == compute_text_hash(base + "Y")

    def test_empty_string(self):
        h = compute_text_hash("")
        assert isinstance(h, str)
        assert len(h) == 64
