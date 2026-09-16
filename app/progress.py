"""Anonymous, device-scoped progress tracking (XP, level, stamps).

No accounts: the frontend generates a random device_id and stores it in
localStorage. SQLite is plenty for a single-machine demo -- no separate
DB service to run.
"""

import os
import sqlite3
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "voicegrader.db")

XP_PER_LEVEL = 20
PASS_THRESHOLD = 80  # overall score needed to earn a stamp for an item

CHARACTER_TIERS = [
    (8, "🦉", "지혜로운 부엉이"),
    (6, "🦜", "앵무새"),
    (4, "🐤", "병아리"),
    (2, "🐣", "아기 새"),
    (1, "🥚", "알"),
]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            overall_score INTEGER NOT NULL,
            xp_earned INTEGER NOT NULL,
            correct INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_device ON attempts(device_id)")
    return conn


def record_attempt(device_id: str, item_id: str, overall_score: int, correct: bool) -> None:
    xp_earned = round(overall_score / 10)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO attempts (device_id, item_id, overall_score, xp_earned, correct) VALUES (?, ?, ?, ?, ?)",
            (device_id, item_id, overall_score, xp_earned, int(correct)),
        )


def character_for_level(level: int) -> tuple[str, str]:
    for threshold, emoji, name in CHARACTER_TIERS:
        if level >= threshold:
            return emoji, name
    return CHARACTER_TIERS[-1][1], CHARACTER_TIERS[-1][2]


@dataclass
class Profile:
    device_id: str
    total_attempts: int
    total_xp: int
    level: int
    xp_into_level: int
    xp_for_next_level: int
    stamps: list[str]
    character_emoji: str
    character_name: str


def get_profile(device_id: str) -> Profile:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(xp_earned), 0) FROM attempts WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        total_attempts, total_xp = row[0], row[1]

        stamp_rows = conn.execute(
            "SELECT DISTINCT item_id FROM attempts WHERE device_id = ? AND overall_score >= ?",
            (device_id, PASS_THRESHOLD),
        ).fetchall()
        stamps = [r[0] for r in stamp_rows]

    level = 1 + total_xp // XP_PER_LEVEL
    xp_into_level = total_xp % XP_PER_LEVEL
    emoji, name = character_for_level(level)

    return Profile(
        device_id=device_id,
        total_attempts=total_attempts,
        total_xp=total_xp,
        level=level,
        xp_into_level=xp_into_level,
        xp_for_next_level=XP_PER_LEVEL,
        stamps=stamps,
        character_emoji=emoji,
        character_name=name,
    )
