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
# Стоп-слова: если есть в тексте — отбрасываем до всякого анализа.
# ---------------------------------------------------------------------------
STOP_WORDS: list[str] = [
    "ищу", "сниму", "сдам", "сдаю", "аренда", "в аренду",
    "продам", "продаю", "куплю", "отдам",
    "сдам виллу", "продам байк", "продам шлем",
    "такси", "обмен валют", "обменяю", "обмен денег",
    "виза", "visa run", "визаран",
    "iphone", "macbook", "ipad",
    "кто знает врача", "подскажите врача", "где купить",
    "вакансия", "резюме", "ищу работу", "ищем сотрудника",
]


# Минимальная длина текста (в символах), чтобы вообще рассматривать сообщение
MIN_TEXT_LENGTH: int = 80
