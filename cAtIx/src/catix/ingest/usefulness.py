"""Usefulness filter: a small decision model scores every incoming message, and the clearly useless ones (greetings,
reactions, "+", canteen menus, ads) are stored but not indexed (see `filtered` in db/schema.sql).

The model is served by llama.cpp at /v1/systemone (https://github.com/ggml-org/llama.cpp/pull/29818, e.g. Kev-0.8B or
Kev-4B). The message is classified as study information, campus news, promo or chatter; the score is the probability
of the first two. A message is filtered when the score is below FILTER_MIN_SCORE. Without FILTER_ROUTE nothing is scored
or filtered. If the server does not answer the message stays unscored and unfiltered (`catix-db refilter` scores it later).
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import httpx

from catix.settings import settings

log = logging.getLogger("catix.usefulness")

MAX_CHARS = 600
WORKERS = 4
QUESTIONS = {
    "c": {
        "type": "choice",
        "instructions": "Classify this message from a university chat or channel.",
        "criteria": {
            "study": "study information: exams, deadlines, homework, schedule changes, rooms, rules, instructions, academic tips",
            "campus": "useful campus news: events, opportunities, competitions, grants, services with dates",
            "promo": "canteen menus, food, lunch invitations, advertisements, marketplace",
            "chatter": "greetings, jokes, reactions, thanks, plus-ones, small talk, questions without information",
        },
    }
}

_http = httpx.Client(timeout=20, limits=httpx.Limits(max_connections=WORKERS * 2))


def enabled() -> bool:
    return settings.filter_route is not None


def score(text: str) -> float:
    """0..1: how likely the message is worth keeping."""
    response = _http.post(
        f"{str(settings.filter_route).rstrip('/')}/systemone",
        json={"state": {"message": text[:MAX_CHARS]}, "questions": QUESTIONS},
    )
    response.raise_for_status()
    probabilities = response.json()["answers"]["c"]["probabilities"]
    return probabilities["study"] + probabilities["campus"]


def score_all(texts: list[str]) -> list[float | None]:
    """Scores in the same order; None where the model could not be asked (or everywhere if the filter is off)."""
    if not enabled() or not texts:
        return [None] * len(texts)

    def one(text: str) -> float | None:
        try:
            return score(text)
        except Exception as e:  # noqa: BLE001 - storing a message must not depend on the filter server
            log.warning("usefulness model unavailable, message stays unscored: %s", e)
            return None

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        return list(executor.map(one, texts))


def is_useless(value: float | None) -> bool:
    return value is not None and value < settings.filter_min_score
