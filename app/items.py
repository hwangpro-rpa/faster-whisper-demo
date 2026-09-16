"""Demo word/sentence bank for the reading drill."""

from dataclasses import dataclass


@dataclass
class Item:
    id: str
    language: str  # "ko" or "en"
    text: str
    level: str  # "word" or "sentence"


ITEMS: list[Item] = [
    Item("en-w1", "en", "rice", "word"),
    Item("en-w2", "en", "light", "word"),
    Item("en-w3", "en", "very", "word"),
    Item("en-w4", "en", "think", "word"),
    Item("en-s1", "en", "She sells seashells by the seashore.", "sentence"),
    Item("en-s2", "en", "Red lorry, yellow lorry.", "sentence"),
    Item("en-s3", "en", "I would like a cup of coffee, please.", "sentence"),
    Item("ko-w1", "ko", "가랑비", "word"),
    Item("ko-w2", "ko", "간장공장", "word"),
    Item("ko-w3", "ko", "실내화", "word"),
    Item("ko-s1", "ko", "저기 있는 저 분은 박 법학박사이고 여기 있는 이 분은 백 법학박사이다.", "sentence"),
    Item("ko-s2", "ko", "오늘 날씨가 정말 좋네요.", "sentence"),
    Item("ko-s3", "ko", "간장 공장 공장장은 강 공장장이다.", "sentence"),
]


def get_items() -> list[Item]:
    return ITEMS


def get_item(item_id: str) -> Item | None:
    for item in ITEMS:
        if item.id == item_id:
            return item
    return None
