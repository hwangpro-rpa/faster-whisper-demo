"""Pronunciation grading.

Grader is the pluggable interface. HeuristicGrader works with no API key
(rule-based confusion-pattern feedback). ClaudeGrader calls the Anthropic
API once ANTHROPIC_API_KEY is set - same interface, drop-in replacement.

get_grader() picks ClaudeGrader automatically when the env var is present,
so switching later needs no code changes.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field


@dataclass
class GradeResult:
    correct: bool
    target_words: list[str]
    recognized_words: list[str]
    diff_ops: list[dict]  # [{op, target, recognized}]
    feedback: str
    provider: str


# (pattern in target word, pattern in what was heard instead, note)
# Matched case-insensitively as substrings; order matters (first match wins).
EN_CONFUSION_RULES = [
    (r"r", r"l", "R/L 발음이 헷갈렸을 수 있어요. 'r'은 혀를 입천장에 닿지 않게 살짝 말아 올리고, 'l'은 혀끝을 윗니 뒤에 붙여서 발음해보세요."),
    (r"l", r"r", "L/R 발음이 헷갈렸을 수 있어요. 'l'은 혀끝을 윗니 뒤에 붙이고, 'r'은 혀를 어디에도 닿지 않게 발음해보세요."),
    (r"f", r"p", "F/P 발음이 섞였을 수 있어요. 'f'는 윗니를 아랫입술에 가볍게 대고 바람을 내보내는 소리예요."),
    (r"v", r"b", "V/B 발음이 섞였을 수 있어요. 'v'는 윗니를 아랫입술에 대고 성대를 울리며 내는 소리, 'b'는 입술을 붙였다 떼는 소리예요."),
    (r"th", r"[sdz]", "th 발음이 s/d로 들렸을 수 있어요. 혀끝을 윗니와 아랫니 사이에 살짝 물고 바람을 내보내듯 발음해보세요."),
    (r"z", r"j", "Z 발음이 J처럼 들렸을 수 있어요. 혀를 치아에 가깝게 두고 성대를 울리며 '즈' 소리를 내보세요."),
]

# Korean: common confusions by consonant/받침 pattern.
KO_CONFUSION_RULES = [
    (r"[ㄹ르라리루레로]", r"[ㄴ느나니누네노]", "ㄹ 받침/초성이 ㄴ으로 들렸을 수 있어요. 혀끝을 윗잇몸에 가볍게 튕기듯 발음해보세요."),
    (r"[ㅓㅕ]", r"[ㅗㅛ]", "'ㅓ'가 'ㅗ'처럼 들렸을 수 있어요. 입을 좀 더 세로로 벌리고 발음해보세요."),
    (r"받침", r"", "받침 발음이 약해서 다음 음절로 흘러들었을 수 있어요. 받침을 조금 더 또렷하게 끊어 발음해보세요."),
]


def _normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[.,!?~…·\"']", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _tokenize(text: str, language: str) -> list[str]:
    norm = _normalize(text)
    if language == "ko":
        # Korean short items are often single words/eojeol; split on whitespace.
        return [w for w in norm.split(" ") if w]
    return [w for w in norm.split(" ") if w]


def _diff_ops(target_words: list[str], recognized_words: list[str]) -> list[dict]:
    sm = difflib.SequenceMatcher(a=target_words, b=recognized_words)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                ops.append({"op": "equal", "target": target_words[i1 + k], "recognized": recognized_words[j1 + k]})
            continue
        t_slice = target_words[i1:i2] or [""]
        r_slice = recognized_words[j1:j2] or [""]
        length = max(len(t_slice), len(r_slice))
        for k in range(length):
            ops.append({
                "op": tag,
                "target": t_slice[k] if k < len(t_slice) else "",
                "recognized": r_slice[k] if k < len(r_slice) else "",
            })
    return ops


class Grader:
    name = "base"

    def grade(self, target_text: str, recognized_text: str, language: str) -> GradeResult:
        raise NotImplementedError


class HeuristicGrader(Grader):
    """Rule-based feedback, no external API needed."""

    name = "heuristic"

    def grade(self, target_text: str, recognized_text: str, language: str) -> GradeResult:
        target_words = _tokenize(target_text, language)
        recognized_words = _tokenize(recognized_text, language)
        ops = _diff_ops(target_words, recognized_words)
        mismatches = [op for op in ops if op["op"] != "equal"]
        correct = len(mismatches) == 0 and len(recognized_words) > 0

        if correct:
            feedback = "정확하게 인식됐어요! 좋은 발음입니다."
        else:
            feedback = self._build_feedback(mismatches, language)

        return GradeResult(
            correct=correct,
            target_words=target_words,
            recognized_words=recognized_words,
            diff_ops=ops,
            feedback=feedback,
            provider=self.name,
        )

    def _build_feedback(self, mismatches: list[dict], language: str) -> str:
        if not mismatches:
            return "인식된 발음이 없어요. 마이크에 조금 더 가까이, 또렷하게 말해보세요."

        rules = EN_CONFUSION_RULES if language == "en" else KO_CONFUSION_RULES
        notes: list[str] = []
        unexplained: list[tuple[str, str]] = []

        for op in mismatches:
            target, recognized = op["target"], op["recognized"]
            if not target and recognized:
                unexplained.append((target, recognized))
                continue
            if target and not recognized:
                notes.append(f"'{target}' 부분이 아예 인식되지 않았어요. 소리가 작았거나 발음이 뭉개졌을 수 있어요.")
                continue

            matched_note = None
            for target_pat, heard_pat, note in rules:
                if re.search(target_pat, target, re.IGNORECASE) and re.search(heard_pat, recognized, re.IGNORECASE):
                    matched_note = note
                    break
            if matched_note:
                notes.append(f"'{target}' → '{recognized}'로 인식됨. {matched_note}")
            else:
                notes.append(f"'{target}'가 '{recognized}'로 다르게 인식됐어요. 각 음절을 또박또박 끊어서 다시 발음해보세요.")

        if unexplained:
            extra = ", ".join(r for _, r in unexplained)
            notes.append(f"추가로 예상에 없던 소리('{extra}')가 섞여 인식됐어요.")

        return " ".join(notes)


class ClaudeGrader(Grader):
    """Calls the Anthropic API for richer, freeform feedback.

    Same GradeResult shape as HeuristicGrader so callers never branch on
    which provider is active.
    """

    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5"):
        import anthropic  # imported lazily so the package is optional until a key exists

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def grade(self, target_text: str, recognized_text: str, language: str) -> GradeResult:
        target_words = _tokenize(target_text, language)
        recognized_words = _tokenize(recognized_text, language)
        ops = _diff_ops(target_words, recognized_words)
        correct = all(op["op"] == "equal" for op in ops) and len(recognized_words) > 0

        prompt = (
            "You are a pronunciation coach. A learner was asked to read this "
            f"target text aloud ({'Korean' if language == 'ko' else 'English'}): \"{target_text}\".\n"
            f"Speech-to-text recognized: \"{recognized_text}\".\n"
            "If they differ, explain in Korean, briefly and kindly, which sounds were likely "
            "mispronounced (based on the mismatch pattern) and give one concrete practice tip. "
            "If they match, give a short encouraging note. Keep it under 3 sentences."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        feedback = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

        return GradeResult(
            correct=correct,
            target_words=target_words,
            recognized_words=recognized_words,
            diff_ops=ops,
            feedback=feedback,
            provider=self.name,
        )


def get_grader() -> Grader:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return ClaudeGrader(api_key=api_key)
    return HeuristicGrader()
