"""
Списки целевых Telegram-чатов, ключевых слов и стоп-слов
для парсера событий на Бали.
"""
import re

# ---------------------------------------------------------------------------
# Целевые чаты для сканирования (Telethon)
# ---------------------------------------------------------------------------
CHATS_TO_LISTEN: list[str] = [
    # News / community
    "@balichatnews", "@businessmenBali", "@Balibizness",
    "@networkers_bali", "@bali_party", "@balifm_afisha",
    "@blizkie_eventss",
    "@balichat", "@balichatdating", "@balichatik", "@balichatnash",
    "@networkingbali", "@voprosBali", "@baliRU", "@Peoplebali",
    "@bali_360", "@balichatflood", "@balistop", "@baliEast",
    "@baliUKR", "@bali_laika", "@balidating", "@plus49",
    # Events / culture
    "@artbali", "@bali_tusa", "@eventsbali", "@balievents",
    "@baligames", "@truth_in_cinema", "@pvbali",
    # Practices / wellness
    "@balisp", "@balipractice", "@Balidance", "@balisoul",
    "@baliyoga",
    "@redkinvilla", "@balimassag", "@ArtTherapyBali",
    "@tranformationgames",
    # Housing / rent (для отзывов и фильтрации)
    "@domanabali", "@domanabalichat", "@balichatarenda",
    "@balirental", "@VillaUbud", "@bali_house", "@allAbout_Bali",
    "@balibike", "@baliauto", "@rentcarbaliopen",
    # Food / health
    "@balifruits", "@balifood", "@balihealth", "@RAWBali",
    "@balibc",
    # Work / jobs
    "@balida21", "@seobali", "@jobsbali", "@balimc", "@BaliManClub",
    "@indonesia_bali",
    # Women / beauty
    "@balichat_woman", "@bali_woman", "@baliwomans", "@balibeauty",
    # Market / money
    "@balirussia", "@balipackage", "@balichatmarket",
    "@bali_baraholka", "@balisale", "@bali_sharing",
    "@Bali_buy_sale", "@designclothing", "@balimoney",
    # Family / sport
    "@balichildren", "@roditelibali",
    "@balifootball", "@balibasket", "@balisurfer",
]


# ---------------------------------------------------------------------------
# Ключевые слова — регулярка. Если совпала — сообщение-кандидат в событие.
# ---------------------------------------------------------------------------
KEYWORDS_REGEX: re.Pattern = re.compile(
    r"(бесплатн|free entry|free|donation|донейшн|донат|вход свободн|"
    r"оплата по сердцу|без оплаты|pay what you want|даром|"
    r"нетворкинг|networking|конференц|бизнес.?завтрак|бизнес.?встреча|"
    r"вечеринк|party|dj|концерт|"
    r"розыгрыш|giveaway|конкурс|"
    r"мастер.?класс|воркшоп|workshop|лекция|семинар|"
    r"meetup|митап|встреча|собрание|"
    r"пробн\w+\s+занят|бесплатн\w+\s+(урок|занят|консультац)|"
    r"открыт\w+\s+(урок|занят|лекц|встреч|микрофон)|"
    r"день\s+открытых\s+дверей|"
    r"приглаша\w+|регистрац|записаться|ждем\s+вас|залетайте|"
    r"каждый\s+(понедельник|вторник|сред[уы]|четверг|пятниц|суббот|воскресень)|"
    r"stand\s*up|стендап|"
    r"сальса|бачата|кизомба|танц|"
    r"english\s+club|разговорный\s+клуб|speaking\s+club|language\s+exchange|"
    r"йога|yoga|ecstatic|медитац|практик|кинопоказ)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Стоп-слова: скомпилированный regex с \b-границами.
# Подстрока "аренда" внутри "аренда байка со скидкой на вечеринке" больше
# не будет ложно срабатывать — только как отдельное слово/фраза.
# ---------------------------------------------------------------------------
_STOP_PATTERNS: list[str] = [
    r"ищу\b", r"сниму\b", r"сдам\b", r"сдаю\b",
    r"\bаренда\b", r"в\s+аренду\b",
    r"продам\b", r"продаю\b", r"куплю\b", r"отдам\b",
    r"такси\b", r"обмен\s+валют", r"обменяю\b", r"обмен\s+денег",
    r"\bвиза\b", r"visa\s+run", r"визаран",
    r"\biphone\b", r"\bmacbook\b", r"\bipad\b",
    r"кто\s+знает\s+врача", r"подскажите\s+врача", r"где\s+купить",
    r"вакансия\b", r"резюме\b", r"ищу\s+работу", r"ищем\s+сотрудника",
]

STOP_RE: re.Pattern = re.compile(
    "|".join(_STOP_PATTERNS),
    re.IGNORECASE,
)

# Оставляем STOP_WORDS для обратной совместимости (используется в тестах/скриптах)
STOP_WORDS: list[str] = [p.replace(r"\b", "").replace(r"\s+", " ") for p in _STOP_PATTERNS]


# Минимальная длина текста (в символах), чтобы вообще рассматривать сообщение
MIN_TEXT_LENGTH: int = 80
