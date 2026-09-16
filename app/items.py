"""Demo word/sentence bank for the reading drill."""

from dataclasses import dataclass


@dataclass
class Item:
    id: str
    language: str  # "ko" or "en"
    text: str
    level: str  # "word" or "sentence" -- exercise shape, used for fluency scoring
    unlock_level: int = 1  # player level required before this item can be drawn
    mode: str = "read"  # "read" or "fill_blank"
    blank_index: int | None = None  # word index (whitespace split) hidden in fill_blank mode
    # fill_blank items must be written so surrounding context makes only one
    # word sensible (e.g. "grind fresh beans and brew a hot cup of ___" can
    # only be "coffee") -- a bare "I drink ___" has too many valid answers
    # (coffee/tea/juice/water/...) to grade against a single fixed text.


ITEMS: list[Item] = [
    Item("en-w1", "en", "rice", "word", unlock_level=1),
    Item("en-w2", "en", "light", "word", unlock_level=1),
    Item("en-w3", "en", "very", "word", unlock_level=1),
    Item("en-w4", "en", "think", "word", unlock_level=1),
    Item("en-s2", "en", "Red lorry, yellow lorry.", "sentence", unlock_level=2),
    Item("en-s1", "en", "She sells seashells by the seashore.", "sentence", unlock_level=3),
    Item("en-s3", "en", "I would like a cup of coffee, please.", "sentence", unlock_level=3),
    Item(
        "en-fb1", "en", "Every morning I grind fresh beans and brew a hot cup of coffee.",
        "sentence", unlock_level=3, mode="fill_blank", blank_index=12,
    ),
    Item("ko-w1", "ko", "가랑비", "word", unlock_level=1),
    Item("ko-w2", "ko", "간장공장", "word", unlock_level=1),
    Item("ko-w3", "ko", "실내화", "word", unlock_level=1),
    Item("ko-s2", "ko", "오늘 날씨가 정말 좋네요.", "sentence", unlock_level=2),
    Item("ko-s3", "ko", "간장 공장 공장장은 강 공장장이다.", "sentence", unlock_level=2),
    Item("ko-s1", "ko", "저기 있는 저 분은 박 법학박사이고 여기 있는 이 분은 백 법학박사이다.", "sentence", unlock_level=3),
    Item(
        "ko-fb1", "ko", "저는 매일 아침 원두를 갈아서 뜨거운 커피를 내려 마셔요.",
        "sentence", unlock_level=3, mode="fill_blank", blank_index=6,
    ),
]


def get_items() -> list[Item]:
    return ITEMS


def get_item(item_id: str) -> Item | None:
    for item in ITEMS:
        if item.id == item_id:
            return item
    return None


def hotwords_for(language: str) -> str:
    """All known target texts for this language, used as a decoding vocabulary
    hint. Includes every item, not just the current one, so it biases Whisper
    toward the demo's domain vocabulary without ever hinting the correct answer.
    """
    return " ".join(item.text for item in ITEMS if item.language == language)
