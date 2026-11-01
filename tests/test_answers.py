"""Answers of the real agent about a synthetic chat with known facts (DeepEval).

Each test asks a question, collects the answer and what the tools returned, and judges it: deterministic checks where a
fact is exact (a date, a room, a language, an invented group) and the local model as a judge (Faithfulness, one test)
where meaning matters. The judge is the same small model that answers, so a failed Faithfulness is a reason to read the
answer, not a verdict. GEval is not used: it kept failing correct answers.
"""

from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from tests.conftest import MONTHS
from tests.helpers import Answer, ContainsAll, LatinShare, MatchesAny, NoMatch, NoOtherDates, ask


def case(question: str, answer: Answer, expected: str | None = None) -> LLMTestCase:
    return LLMTestCase(input=question, actual_output=answer.body, expected_output=expected, retrieval_context=answer.tool_results)


def test_exact_date_and_room(agent, chat, facts):
    question = "Когда контрольная по ботанике и в какой аудитории?"
    answer = ask(agent, question)
    assert_test(case(question, answer), [ContainsAll([facts["botany_text"], "14:00", "301"], name="DateTimeAndRoom")])


def test_relative_date_is_resolved(agent, chat, facts):
    """The message says 'послезавтра' and was written today: the answer must give the date two days from now."""
    question = "Когда экскурсия на птицефабрику?"
    answer = ask(agent, question)
    day = facts["excursion"]
    month = MONTHS[day.month - 1]
    assert_test(
        case(question, answer),
        [MatchesAny([rf"\b{day.day}\s+{month}", rf"\b{day.day:02d}\.{day.month:02d}"], name="ResolvedDate"), ContainsAll(["8:00"], name="Time")],
    )


def test_answer_is_grounded_in_the_messages(agent, judge, chat):
    """Only the synthetic chat is searchable: the answer must stay within its two messages. With the real chats mixed in
    (announcements about buildings 1-7) the model fills the gaps with 'the administration says' and 'ask the warden'."""
    question = "Когда смена белья в корпусе 9?"
    answer = ask(agent, question, only_chats={chat})
    assert_test(case(question, answer), [FaithfulnessMetric(threshold=0.7, model=judge, async_mode=False, include_reason=True)])


def test_does_not_extrapolate_a_schedule(agent, chat, facts):
    """Regression: the bot once announced 'next change on Monday 19 October' when the message gave only today.
    The messages give: today 14:00-17:00, and an old one 'on Mondays'. No other calendar date may appear."""
    question = "Когда смена белья в корпусе 9?"
    answer = ask(agent, question)
    today = facts["today"]
    assert_test(case(question, answer), [NoOtherDates([(today.day, today.month)])])


def test_english_question_gets_an_english_answer(agent, chat):
    """Regression: an English question was answered in Russian after a Russian conversation."""
    question = "When is the botany test and in which room?"
    answer = ask(agent, question)
    assert_test(case(question, answer), [LatinShare(at_least=0.8, name="EnglishAnswer")])


def test_russian_question_gets_a_russian_answer(agent, chat):
    question = "Во сколько сбор на экскурсию на птицефабрику?"
    answer = ask(agent, question)
    assert_test(case(question, answer), [LatinShare(at_most=0.3, name="RussianAnswer")])


# "Ваша группа — B26-DSAI-01": a group stated as fact. A refusal that gives an example code ("например, B26-DSAI-04") is fine.
GROUP_CLAIMS = [
    r"ваша\s+(учебная\s+)?группа\s*[—–:-]?\s*(это\s+)?[BM]\d{2}-",
    r"вы\s+(учитесь\s+)?в\s+группе\s+[BM]\d{2}-",
    r"your\s+(study\s+)?group\s+is\s+[BM]\d{2}-",
]


def test_does_not_invent_the_askers_group(agent):
    """Regression: for a user whose group is unknown the assistant once answered 'Ваша группа — B26-DSAI-01', a code it
    made up (the prompt's examples look like one). It happened in about 1 of 4 answers, so the question is asked six times."""
    question = "Какая у меня группа?"
    for _ in range(6):
        answer = ask(agent, question)
        assert_test(case(question, answer), [NoMatch(GROUP_CLAIMS, name="NoInventedGroup")])
