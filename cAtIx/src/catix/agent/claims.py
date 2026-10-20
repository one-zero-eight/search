"""A check of the final answer in code: claims about who said something, and about what was "not announced".

A small model fills gaps with plausible attributions: "the administration says", "ask the head of the building", "it was
not announced". The prompt forbids it and the model still does it, so the sentences are checked here against what the
tools returned in this turn. A claim stays only if the same words appear in the results, or (for "official") a result
comes from a chat an admin marked official. Everything else is cut out of the answer and logged.
"""

import logging
import re

log = logging.getLogger("catix.claims")

# (pattern, what it claims). Only ATTRIBUTIONS are checked ("the administration says", "according to the dean's office",
# "it was not announced", "an official announcement"), never mere mentions: "contact the dean's office" or "the official
# Telegram channel: t.me/…" is advice or a link, not a claim about where a message came from. \b keeps "неофициальный"
# (unofficial) out of "официальный".
_WHO = r"(?:администраци\w*|деканат\w*|\bdean(?:'s|’s)?\s+office|\badministration|\bwarden|\bheadman)"
CLAIMS: list[tuple[str, str, str]] = [
    (rf"(?:от|со\s+стороны|согласно|по\s+(?:данным|информации|сообщениям)|сообщени\w+\s+от)\s+(?:\w+\s+){{0,2}}{_WHO}", "the administration or the dean's office said it", _WHO),
    (rf"{_WHO}(?:\s+\w+){{0,2}}\s+(?:сообщает|сообщил\w*|объявил\w*|объявляет|анонсировал\w*|написал\w*|пишет|указал\w*|информирует|публикует|опубликовал\w*|says?|said|announced|states?|stated|published|posted)\b", "the administration or the dean's office said it", _WHO),
    (rf"\b(?:according\s+to|per|announced\s+by|reported\s+by|from)\s+(?:the\s+)?{_WHO}", "the administration or the dean's office said it", _WHO),
    (r"\bстарост\w*\s+(?:корпуса|потока|группы|общежития)|\b(?:у|к|со)\s+старост\w+|\bhead\s+of\s+the\s+(?:building|dorm)|\bwarden\b|\bheadman\b", "the head of a building or a year is involved", r"\bстарост|\bwarden|\bheadman|head\s+of\s+the\s+(?:building|dorm)"),
    (r"\bне\s+(?:анонсир|объявл|публиковал)\w*|\bnot\s+(?:been\s+)?announced\b", "it was not announced", r"\bне\s+(?:анонсир|объявл|публиковал)|\bnot\s+(?:been\s+)?announced"),
    (r"\bофициальн\w+\s+(?:объявлени|анонс|сообщени|информаци|источник|данн|заявлени)\w*|\bofficial\s+(?:announcement|source|information|statement|notice|message)s?\b", "it is official", r"\bофициальн|\bofficial\b"),
]
OFFICIAL_RESULT = re.compile(r'"official"\s*:\s*true')
OFFICIAL_KEY = re.compile(r'"official"\s*:\s*(?:true|false)')
SENTENCES = re.compile(r"((?<=[.!?])\s+|\n+)")


def check(answer: str, evidence: str) -> tuple[str, list[str]]:
    """The answer without the unsupported sentences, and those sentences. `evidence` is what the tools returned."""
    official_seen = bool(OFFICIAL_RESULT.search(evidence))
    text = OFFICIAL_KEY.sub("", evidence).lower()  # the key `"official": false` is not a statement about anything
    parts = SENTENCES.split(answer)  # sentence, separator, sentence, ...
    kept: list[str] = []
    dropped: list[str] = []
    for i in range(0, len(parts), 2):
        sentence, separator = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        reason = _unsupported(sentence, text, official_seen)
        if reason:
            dropped.append(f"{sentence.strip()}  ({reason})")
        else:
            kept.append(sentence + separator)
    if not dropped:
        return answer, []
    cleaned = re.sub(r"\n{3,}", "\n\n", "".join(kept)).strip()
    if not cleaned:  # everything was a claim without support
        cleaned = "Не нашёл в сообщениях подтверждения." if re.search(r"[а-яё]", answer.lower()) else "I found no message that confirms this."
    log.warning("cut %d unsupported sentence(s) from the answer: %s", len(dropped), dropped)
    return cleaned, dropped


def _unsupported(sentence: str, evidence: str, official_seen: bool) -> str | None:
    lowered = sentence.lower()
    for pattern, claim, support in CLAIMS:
        if not re.search(pattern, lowered):
            continue
        if claim == "it is official" and official_seen:
            continue
        if re.search(support, evidence):  # the results mention the same thing (a message signed by the administration…)
            continue
        return claim
    return None
