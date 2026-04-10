from enum import Enum


class EventStatus(str, Enum):
    PENDING = "pending"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
