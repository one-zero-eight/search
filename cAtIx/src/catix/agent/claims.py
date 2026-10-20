"""A check of the final answer in code: claims about who said something, and about what was "not announced".

A small model fills gaps with plausible attributions: "the administration says", "ask the head of the building", "it was
not announced". The prompt forbids it and the model still does it, so the sentences are checked here against what the
tools returned in this turn. A claim stays only if the same words appear in the results, or (for "official") a result
comes from a chat an admin marked official. Everything else is cut out of the answer and logged.
"""

import logging
import re

log = logging.getLogger("catix.claims")

# (pattern, what it claims). \b keeps "неофициальный" (unofficial) out of "официальный".
CLAIMS: list[tuple[str, str]] = [
    (r"администрац\w*|\badministration\b", "the administration said it"),
    (r"деканат\w*|\bdean(?:'s|’s)? office\b", "the dean's office said it"),
    (r"\bстарост\w*|\bheadman\b|\bwarden\b", "the head of a building or a year is involved"),
    (r"\bне\s+(?:анонсир|объявл|публиковал)\w*|\bnot\s+(?:been\s+)?announced\b", "it was not announced"),
    (r"\bофициальн\w*|\bofficial\w*", "it is official"),
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
    for pattern, claim in CLAIMS:
        if not re.search(pattern, lowered):
            continue
        if claim == "it is official" and official_seen:
            continue
        if re.search(pattern, evidence):  # the results use the same words
            continue
        return claim
    return None
