"""Does the model tell calendar items (reschedules, room changes, cancellations, new events) from questions, rumours and
jokes? (catix.worker.changes.extract, judged with DeepEval's exact label match.)"""

from datetime import datetime

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from catix.db.rows import MessageToRead
from catix.settings import settings
from catix.worker import changes
from tests.helpers import SameLabel

CASES = [  # (message, label)
    ("Ребята, лекцию по матану завтра перенесли на 16:30, аудитория 108", "change"),
    ("Контрольная по ИТП в пятницу теперь будет в 313, а не в 301", "change"),
    ("Завтрашний семинар по дискретке отменяется", "change"),
    ("Lab on Friday has been moved to 18:00 in room 105", "change"),
    ("В среду в 18:00 в 108 будет гостевая лекция от Яндекса про ML", "change"),
    ("Дедлайн по лабе 3 — через неделю, 23:59", "change"),
    ("Напоминаю, что завтра в 10:00 в 214 хакатон по робототехнике", "change"),
    ("а когда перенесут лекцию? кто-нибудь знает", "none"),
    ("лол вчера пару отменили, красота", "none"),
    ("кажется контрольную отменят, но это не точно", "none"),
    ("Перенесу свои вещи в комнату завтра", "none"),
    ("Ребята, перенесли на другой день", "none"),
    ("Кто-нибудь знает когда будет мидтерм по матану?", "none"),
    ("вчера был прикольный хакатон, всем спасибо", "none"),
    ("Скиньте конспект лекции по дискретке пожалуйста", "none"),
    ("Всем привет! Кто идет вечером в столовую", "none"),
]


@pytest.fixture(scope="module")
def model():
    return changes._model()


@pytest.mark.parametrize("text,label", CASES, ids=[t[:40] for t, _ in CASES])
def test_detects_calendar_items(model, text, label):
    sent = datetime.now(settings.tz).replace(hour=12, minute=0)  # "завтра" must lie ahead: past events are dropped
    found = changes.extract(model, MessageToRead(0, sent, text, "Матан B26", None, False))
    assert_test(
        LLMTestCase(input=text, actual_output="change" if found else "none", expected_output=label),
        [SameLabel()],
    )
