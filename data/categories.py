from enum import Enum

class EventCategory(str, Enum):
    FREE = "Free"
    PAID = "Paid"
    NETWORKING = "Networking"
    PARTY = "Party"
    SPAM = "Spam"
    UNKNOWN = "Unknown"

CATEGORY_ICONS = {
    "Free": "🆓",
    "Paid": "💰",
    "Networking": "🤝",
    "Party": "🎉",
    "Spam": "💩",
    "Unknown": "❓"
}
