"""Does the model tell calendar items (reschedules, room changes, cancellations, new events) from questions, rumours
and jokes? (changes.extract)
Usage: uv run python experiments/eval_changes.py"""

import time
from datetime import datetime

from catix.worker import changes
from catix.db.rows import MessageToRead
from catix.settings import settings

CASES = [  # (message, is it a change?)
    ("Ребята, лекцию по матану завтра перенесли на 16:30, аудитория 108", True),
    ("Контрольная по ИТП в пятницу теперь будет в 313, а не в 301", True),
    ("Завтрашний семинар по дискретке отменяется", True),
    ("Lab on Friday has been moved to 18:00 in room 105", True),
    ("а когда перенесут лекцию? кто-нибудь знает", False),
    ("лол вчера пару отменили, красота", False),
    ("кажется контрольную отменят, но это не точно", False),
    ("Перенесу свои вещи в комнату завтра", False),
    ("Ребята, перенесли на другой день", False),
    ("В среду 21 октября в 18:00 в 108 будет гостевая лекция от Яндекса про ML", True),
    ("Дедлайн по лабе 3 — 25 октября, 23:59", True),
    ("Напоминаю, что завтра в 10:00 в 214 хакатон по робототехнике", True),
    ("Кто-нибудь знает когда будет мидтерм по матану?", False),
    ("вчера был прикольный хакатон, всем спасибо", False),
    ("Скиньте конспект лекции по дискретке пожалуйста", False),
    ("Всем привет! Кто идет вечером в столовую", False),
]


def main() -> None:
    model = changes._model()
    sent = datetime.now(settings.tz).replace(hour=12, minute=0)  # "завтра" must lie ahead: past events are dropped
    ok = 0
    for text, expected in CASES:
        row = MessageToRead(0, sent, text, "Матан B26", None, False)
        started = time.monotonic()
        try:
            change = changes.extract(model, row)
        except Exception as e:  # noqa: BLE001
            change = None
            print("error:", type(e).__name__, e)
        ok += (change is not None) == expected
        shown = (change.kind, change.subject, f"{change.day:%d.%m} {change.start_time or 'весь день'}", change.room) if change else None
        print("✓" if (change is not None) == expected else "✗", text[:62], "->", shown, f"({time.monotonic() - started:.1f}s)")
    print(f"{ok}/{len(CASES)} correct")


if __name__ == "__main__":
    main()
