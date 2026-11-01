"""Rules for messages that are not worth storing: a bare greeting or a text too short to mean anything.

Only what is certainly noise is dropped, so that nothing useful is lost without a model to judge it:
- no letters or digits at all: "+", "👍", "😂😂😂", "!!!";
- a few letters and no digit: "ок", "да", "ага", "хм" (a digit keeps "108" or "5 нояб": a room, a date);
- a picture, sticker, GIF, video or voice message without a caption (the text is just "[file: sticker.webp]");
  documents keep their names, "exam_2025.pdf" is worth finding;
- nothing but a greeting and words of address: "Привет", "Всем привет!", "Доброе утро, ребята", "Hi guys",
  "Good morning everyone". A greeting followed by anything else ("Hi guys! Reminder: test today") is kept.
Messages with a link or a document name are kept: they carry more than the greeting.
"""

import re

from catix.settings import settings

MAX_TINY_LETTERS = 3  # "нет" is noise, "дата" is not.

# "доброе утро", "good evening": the time of day is part of the greeting, not a word of its own.
_PHRASE = re.compile(
    r"\b(?:good|добр\w*)\s+(?:morning|afternoon|evening|night|day|утро|утра|день|дня|вечер|вечера|ночи|ночь)\b"
)
_GREETING = "GREETING"
_GREETING_WORDS = {
    "привет", "приветик", "приветики", "приветствую", "здравствуй", "здравствуйте", "здрасте", "здрасьте", "здарова",
    "здаров", "салют", "хай", "хей", "хэй", "йоу", "ку", "hello", "hi", "hey", "hiya", "howdy", "greetings", "hola", "yo",
}
# Words of address and filler around a greeting.
_ADDRESS_WORDS = {
    "всем", "всех", "ребята", "ребят", "ребятки", "друзья", "народ", "коллеги", "дорогие", "уважаемые", "товарищи",
    "студенты", "все", "и", "а", "ну", "всеми", "everyone", "everybody", "all", "guys", "folks", "friends", "team",
    "there", "dear", "students", "and", "again", "снова", "опять", "еще", "всё",
}
# The text of a message that is only a media file (see userbot.py: "[file: <name>]" is all a captionless one has).
_MEDIA_ONLY = re.compile(
    r"\[file: [^\]]*\.(?:jpe?g|png|gif|webp|webm|mp4|mov|mkv|avi|m4v|mp3|ogg|oga|opus|m4a|wav|tgs|heic)\]", re.I
)
_URL = re.compile(r"https?://|www\.|t\.me/", re.I)
_WORD = re.compile(r"[^\W_]+")


def is_noise(text: str) -> bool:
    """True for text that is certainly not worth storing."""
    if _MEDIA_ONLY.fullmatch(text.strip()):
        return True
    if "[file:" in text or _URL.search(text):
        return False
    folded = text.casefold().replace("ё", "е")
    words = _WORD.findall(folded)
    if not words:
        return True  # Only symbols and emoji.
    if any(ch.isdigit() for ch in folded):
        return False
    if sum(len(word) for word in words) <= MAX_TINY_LETTERS:
        return True
    marked = _WORD.findall(_PHRASE.sub(_GREETING.casefold(), re.sub(r"@\w+", " ", folded)))
    greeting = _GREETING.casefold()
    return any(w == greeting or w in _GREETING_WORDS for w in marked) and all(
        w == greeting or w in _GREETING_WORDS or w in _ADDRESS_WORDS for w in marked
    )


def enabled() -> bool:
    return settings.drop_noise
