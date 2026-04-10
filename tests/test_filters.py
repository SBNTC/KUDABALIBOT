"""
Тесты фильтрации сообщений: _passes_filters, STOP_RE, KEYWORDS_REGEX.

Чистые функции — не требуют БД или внешних сервисов.
"""
import pytest
import sys
import os

# Позволяем импортировать из корня проекта без установки пакета
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.chats import KEYWORDS_REGEX, STOP_RE, MIN_TEXT_LENGTH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def passes_filters(text: str) -> bool:
    """Локальная копия логики _passes_filters (без импорта БД)."""
    if not text or len(text) < MIN_TEXT_LENGTH:
        return False
    if STOP_RE.search(text):
        return False
    return bool(KEYWORDS_REGEX.search(text))


# ---------------------------------------------------------------------------
# Длина текста
# ---------------------------------------------------------------------------

class TestLengthFilter:
    def test_empty_string_rejected(self):
        assert passes_filters("") is False

    def test_short_string_rejected(self):
        short = "вечеринка"
        assert len(short) < MIN_TEXT_LENGTH
        assert passes_filters(short) is False

    def test_exact_min_length_with_keyword(self):
        # ровно MIN_TEXT_LENGTH символов, содержит keyword
        text = ("йога " * 20)[:MIN_TEXT_LENGTH]
        assert len(text) >= MIN_TEXT_LENGTH
        # может не пройти если стоп-слово попадёт случайно — здесь всё чисто
        assert passes_filters(text) is True


# ---------------------------------------------------------------------------
# Стоп-слова (STOP_RE)
# ---------------------------------------------------------------------------

class TestStopWords:
    @pytest.mark.parametrize("text", [
        "Ищу" + " " * 5 + "квартиру на Бали, помогите пожалуйста найти что-то нормальное",
        "сдаю апартаменты" + " " * 60 + "пишите в лс",
        "Аренда байка со скидкой, пишите в личку, очень срочно нужно продать",
        "в аренду вилла на три месяца, цена договорная, бали 2024",
        "куплю scooter honda, помогите найти на Бали, очень нужен",
        "продаю мотоцикл, недорого, срочно" + " " * 50,
        "Такси из аэропорта Денпасар, дёшево и быстро, пишите",
        "iphone 15 pro max купить на бали недорого, срочно",
        "Вакансия: ищем менеджера на Бали, опыт не нужен, з/п высокая",
        "Резюме: ищу работу, есть опыт в маркетинге и продажах",
    ])
    def test_stop_words_block(self, text: str):
        long_text = text.ljust(MIN_TEXT_LENGTH + 10)
        assert passes_filters(long_text) is False, f"Should be blocked: {text[:50]}"

    def test_stop_word_as_substring_does_not_block(self):
        # "аренда" внутри слова не срабатывает (word boundary \b в паттерне)
        # Но "аренда" отдельным словом срабатывает
        text = ("мероприятие по йоге и медитации на Бали, приглашаем всех желающих "
                "практиков, вход свободный, без регистрации, каждую субботу")
        assert passes_filters(text) is True


# ---------------------------------------------------------------------------
# Ключевые слова (KEYWORDS_REGEX)
# ---------------------------------------------------------------------------

class TestKeywords:
    @pytest.mark.parametrize("keyword_text", [
        "Бесплатная йога сегодня в 7 утра у пляжа Семиньяк, приходите все!",
        "Нетворкинг для предпринимателей на Бали в эту субботу вечером",
        "Мастер-класс по акварели: воркшоп для начинающих художников в Убуде",
        "Party tonight at Potato Head, free entry before midnight, DJ set",
        "Открытый урок по испанскому языку, разговорный клуб Ubud",
        "Йога и медитация каждое воскресенье на рисовых полях Убуда",
        "Stand up comedy show на английском, приходите смеяться вместе",
        "Сальса вечеринка в пятницу, бачата и кизомба до утра",
        "Ecstatic dance каждую субботу, вход по донейшн",
        "Концерт живой музыки у океана, donation based вечер",
        "Giveaway: розыгрыш бесплатного урока йоги среди подписчиков",
        "English club: speaking club по средам в кафе на Чангу",
        "Кинопоказ под открытым небом, вход свободный для всех",
        "Бизнес-завтрак для предпринимателей в Денпасаре в среду",
    ])
    def test_keywords_pass(self, keyword_text: str):
        long_text = keyword_text.ljust(MIN_TEXT_LENGTH + 5)
        assert passes_filters(long_text) is True, f"Should pass: {keyword_text[:50]}"

    def test_no_keyword_rejected(self):
        text = ("Сегодня прекрасная погода на Бали, температура 30 градусов, "
                "море теплое, хочется просто лежать на пляже и ни о чем не думать.")
        assert passes_filters(text) is False


# ---------------------------------------------------------------------------
# Комбинированные сценарии
# ---------------------------------------------------------------------------

class TestCombined:
    def test_keyword_plus_stop_word_blocked(self):
        # содержит keyword И стоп-слово — стоп-слово побеждает
        text = ("Аренда зала для йоги на Бали, мастер-класс, "
                "место красивое, приходите все желающие практики")
        assert passes_filters(text) is False

    def test_event_announcement_passes(self):
        text = ("Приглашаем на открытый урок по йоге! Каждую субботу в 7:00 "
                "на пляже Берава. Вход свободный, donation welcome. "
                "Регистрация не нужна, просто приходите.")
        assert passes_filters(text) is True

    def test_unicode_case_insensitive(self):
        text = ("ЙОГА И МЕДИТАЦИЯ — открытая практика в парке, "
                "приглашаем всех, бесплатно, каждое утро на рассвете!")
        assert passes_filters(text) is True
