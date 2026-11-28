"""Small real-extractor probe; synthetic text only, no calendar storage or service writes."""
from datetime import datetime, timedelta

import pytest

from catix.agent import events, tracing
from catix.common.citations import AnswerSource
from catix.settings import settings

pytestmark = pytest.mark.model


def test_same_subject_class_does_not_hide_independent_homework_deadline():
    day = (datetime.now(settings.tz) + timedelta(days=1)).date().isoformat()
    answer = ('Завтра Mathematical Analysis в 10:00. '
              'Дедлайн домашней работы по Mathematical Analysis завтра [1].')
    sources = [AnswerSource(number=1, title='Учебный чат', url='https://example.org/deadline', kind='chat')]
    origins = {'service': True, 'excluded': [{'names': ['Mathematical Analysis'], 'day': day, 'time': '10:00'}]}
    with tracing.private(True):
        found = events.extract(answer, sources=sources, origins=origins)
    assert len(found) == 1, found
    assert 'дедлайн' in found[0]['title'].casefold(), found
    assert found[0]['source_url'] == 'https://example.org/deadline'
    assert found[0]['all_day'] is True and found[0]['ends_at'] is None
