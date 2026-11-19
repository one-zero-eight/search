"""A check of the final answer in code: claims about who said something, and about what was "not announced".

A small model fills gaps with plausible attributions: "the administration says", "ask the head of the building", "it was
not announced". The prompt forbids it and the model still does it, so the sentences are checked here against what the
tools returned in this turn. Attributions require support in the cited records; official status requires every cited
record to have trusted `official: true` metadata. Unresolved or conflicting refs cannot establish an attribution.
"""

import json
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
REFS = re.compile(r"\[\s*(m\d+(?:\s*[,;]\s*m\d+)*)\s*\]")
SENTENCES = re.compile(r"((?<=[.!?])\s+|\n+)")


def _records(evidence: str) -> dict[str, list[dict]]:
    """Index structured tool records only; JSON-looking text inside a record is never metadata."""
    records: dict[str, list[dict]] = {}

    def walk(value):
        if isinstance(value, dict):
            ref = value.get("ref")
            if isinstance(ref, str) and re.fullmatch(r"m\d+", ref):
                records.setdefault(ref, []).append(value)
                return
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    decoder = json.JSONDecoder()
    position = 0
    while position < len(evidence):
        position += len(evidence[position:]) - len(evidence[position:].lstrip())
        if position == len(evidence):
            break
        try:
            value, position = decoder.raw_decode(evidence, position)
        except json.JSONDecodeError:
            # An unstructured helper report is not a source record.
            end = evidence.find("\n", position)
            if end < 0:
                break
            position = end + 1
        else:
            walk(value)
    return records


def check(answer: str, evidence: str) -> tuple[str, list[str]]:
    """The answer without the unsupported sentences, and those sentences. `evidence` is what the tools returned."""
    records = _records(evidence)
    parts = SENTENCES.split(answer)  # sentence, separator, sentence, ...
    kept: list[str] = []
    dropped: list[str] = []
    for i in range(0, len(parts), 2):
        sentence, separator = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        refs = {ref for match in REFS.finditer(sentence) for ref in re.findall(r"m\d+", match.group(1))}
        cited = [record for ref in refs for record in records.get(ref, [])]
        resolved = bool(refs) and all(ref in records for ref in refs)
        reason = _unsupported(sentence, cited if resolved else [])
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


def _unsupported(sentence: str, records: list[dict]) -> str | None:
    lowered = sentence.lower()
    for pattern, claim, support in CLAIMS:
        if not re.search(pattern, lowered):
            continue
        if claim == "it is official":
            if records and all(record.get("official") is True for record in records):
                continue
        elif records and all(re.search(support, str(record.get("text", "")).lower()) for record in records):
            continue
        return claim
    return None
