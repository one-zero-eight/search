"""What RunGuardMiddleware does and does not do, without a model (DeepEval).

It never picks tools for the model (an earlier version added a search_userbot_chats call itself: the model answered, that answer
was thrown away and the run asked again, and the Telegram draft showed it). It only keeps a run from ending badly: a repeated
call is not executed again, a tool call written as text is repaired, the last model call has no tools and must answer.
"""

import types

from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core
from catix.agent.core import RunGuardMiddleware
from tests.helpers import ContainsAll

SEARCH = {"name": "search_chats", "args": {"queries": ["мидтерм итп"]}, "id": "call-1", "type": "tool_call"}
TOOLS = [types.SimpleNamespace(name="search_chats"), types.SimpleNamespace(name="search_userbot_chats")]


class Req:
    """A ModelRequest with the few things the guard reads, and `override` like the real one."""

    def __init__(self, ai_messages: int, system="base prompt"):
        self.messages = [HumanMessage("вопрос"), *[AIMessage(content="", tool_calls=[SEARCH]) for _ in range(ai_messages)]]
        self.tools, self.system_message, self.tool_choice = TOOLS, types.SimpleNamespace(text=system), None

    def override(self, **changes):
        clone = Req(0)
        clone.__dict__.update(self.__dict__ | changes)
        return clone


def test_the_guard_does_not_add_tool_calls_the_model_did_not_make():
    guard = RunGuardMiddleware()
    assert not hasattr(guard, "_userbot_alongside") and not hasattr(guard, "_userbot_call")
    response = ModelResponse(result=[AIMessage(content="", tool_calls=[SEARCH])])
    seen = []
    result = guard.wrap_model_call(Req(1), lambda request: seen.append(request) or response)
    assert [c["name"] for c in result.result[-1].tool_calls] == ["search_chats"]  # only the model's own call
    assert seen[0].tools == TOOLS  # the request went on untouched


def test_a_final_answer_is_not_followed_by_a_forced_search():
    answer = AIMessage(content="Мидтерм в среду [m1].")
    result = RunGuardMiddleware().wrap_model_call(Req(1), lambda request: ModelResponse(result=[answer]))
    assert result.result[-1] is answer and not answer.tool_calls


def test_the_last_call_may_not_call_tools_and_has_an_order_to_answer():
    """The tools and the system prompt stay as they were (the start of the request is the model server's cache): the
    call only forbids tool calls and adds the order after the conversation."""
    guard = RunGuardMiddleware()
    early = guard._final(Req(1))
    assert early.tools == TOOLS and early.system_message.text == "base prompt" and early.tool_choice is None
    before = Req(core.settings.agent_max_model_calls - 1)
    last = guard._final(before)
    assert last.tools == TOOLS and last.system_message.text == "base prompt" and last.tool_choice == "none"
    assert last.messages[:-1] == before.messages
    assert_test(LLMTestCase(input="", actual_output=str(last.messages[-1].content)), [ContainsAll(["You have used your tool budget"], name="OrderToAnswer")])


def test_once_the_reads_are_spent_the_next_call_is_the_report():
    """Told in read_wiki's result to report, the model read on (the trace of 'регламент организации ИТ-поддержки'): after
    MAX_READS reads that gave text the docs helper may not call tools. A read that found nothing does not count."""
    import json

    def read(n: int, pieces: list) -> list:
        call = {"name": "read_wiki", "args": {"page": "/raw/x.md", "clause": str(n)}, "id": f"r{n}", "type": "tool_call"}
        return [AIMessage(content="", tool_calls=[call]), ToolMessage(content=json.dumps({"pieces": pieces}), tool_call_id=f"r{n}", name="read_wiki")]

    guard = RunGuardMiddleware({"search_wiki", "read_wiki"})
    req = Req(0)
    req.messages = [HumanMessage("регламент ИТ-поддержки"), *read(1, [{"text": "…"}]), *read(2, [])]
    assert guard._final(req).tool_choice is None  # one read gave text, one found nothing: one more may be made
    req.messages += read(3, [{"text": "…"}])
    assert guard._final(req).tool_choice == "none" and guard._final(req).tools == TOOLS
    assert RunGuardMiddleware({"search_chats"})._final(req).tool_choice is None  # (a helper without read_wiki)


def test_after_two_empty_searches_in_a_row_the_next_call_is_the_report():
    """The chats helper reworded an empty search four times ('как получить права администратора на компьютер'): one
    rewording is allowed, then it reports. Two searches side by side in one call are one try; one that found something
    starts the count again."""
    import json

    def turn(n: int, *totals: int) -> list:
        calls = [{"name": "search_chats", "args": {"queries": [f"q{n}{i}"]}, "id": f"s{n}{i}", "type": "tool_call"} for i in range(len(totals))]
        return [AIMessage(content="", tool_calls=calls), *(ToolMessage(content=json.dumps({"total": t, "messages": []}), tool_call_id=c["id"], name="search_chats")
                                                           for c, t in zip(calls, totals))]

    guard = RunGuardMiddleware({"search_chats", "search_userbot_chats"})
    req = Req(0)
    req.messages = [HumanMessage("права администратора"), *turn(1, 0, 0)]
    assert guard._final(req).tool_choice is None  # one empty try (two searches side by side): one rewording may follow
    req.messages += turn(2, 0)
    assert guard._final(req).tool_choice == "none"
    req.messages = [HumanMessage("права администратора"), *turn(1, 0), *turn(2, 3), *turn(3, 0)]
    assert guard._final(req).tool_choice is None  # (the second found something: the empty ones are not in a row)


def test_a_chat_search_with_nothing_about_the_question_it_had_not_found_before_is_empty():
    """On 'какие требования к компьютеру и камере на дистанционном экзамене' every chat search found 3 to 6 messages (midterm
    notices, arrival in Russia) and the helper searched 5 rounds; on 'сколько нужно заниматься физкультурой' it found the
    one post on physical education again and again. The refs of the messages about the question go with the result as its
    artifact, which the model does not see."""
    import json

    def turn(n: int, relevant: list | None) -> list:
        call = {"name": "search_chats", "args": {"queries": [f"q{n}"]}, "id": f"s{n}", "type": "tool_call"}
        result = ToolMessage(content=json.dumps({"total": 4, "messages": [{}] * 4}), tool_call_id=f"s{n}", name="search_chats",
                             artifact=None if relevant is None else {"relevant": relevant})
        return [AIMessage(content="", tool_calls=[call]), result]

    guard = RunGuardMiddleware({"search_chats", "search_userbot_chats"})
    req = Req(0)
    req.messages = [HumanMessage("требования к камере"), *turn(1, []), *turn(2, [])]
    assert guard._final(req).tool_choice == "none"
    req.messages = [HumanMessage("требования к камере"), *turn(1, []), *turn(2, ["m1"])]
    assert guard._final(req).tool_choice is None  # (one is about the question)
    req.messages = [HumanMessage("физкультура"), *turn(1, ["m1"]), *turn(2, ["m1"]), *turn(3, ["m1"])]
    assert guard._final(req).tool_choice == "none"  # (the same post, found again twice)
    req.messages = [HumanMessage("физкультура"), *turn(1, ["m1"]), *turn(2, ["m1"]), *turn(3, ["m1", "m5"])]
    assert guard._final(req).tool_choice is None
    req.messages = [HumanMessage("требования к камере"), *turn(1, None), *turn(2, None)]
    assert guard._final(req).tool_choice is None  # (not scored: the reranker was down)


def test_after_two_rounds_of_reports_with_sources_the_supervisor_answers():
    """Given a report with sources, the supervisor asked the docs helper for more details four times over ('как
    перезачесть курсы, пройденные в другом вузе', 137 s). One more round is its choice, then it answers; a report without
    a source (the helper failed, or found nothing) does not count."""

    def ask(n: int, report: str) -> list:
        call = {"name": "ask_docs", "args": {"question": f"q{n}"}, "id": f"a{n}", "type": "tool_call"}
        return [AIMessage(content="", tool_calls=[call]), ToolMessage(content=report, tool_call_id=f"a{n}", name="ask_docs")]

    guard = RunGuardMiddleware({"ask_docs", "ask_chats", "ask_campus"})
    req = Req(0)
    req.messages = [HumanMessage("как перезачесть курсы"), *ask(1, core.TOOL_FAILURE_ANSWER), *ask(2, "Решает аттестационная комиссия [m1].")]
    assert guard._final(req).tool_choice is None
    req.messages += ask(3, "Заявление подаётся председателю комиссии [m8][m9].")
    assert guard._final(req).tool_choice == "none" and guard._final(req).tools == TOOLS


def test_a_helper_that_reported_with_sources_is_not_asked_again_and_the_next_call_is_the_answer():
    """The supervisor reworded 'сколько нужно заниматься физкультурой' to 'сколько часов в неделю…' for the docs helper: 25 s
    more for what the first report had. A helper that failed or found nothing may be asked again, another helper too."""

    def ask(n: int, helper: str = "ask_docs") -> dict:
        return {"name": helper, "args": {"question": f"q{n}"}, "id": f"a{n}", "type": "tool_call"}

    def report(n: int, text: str) -> ToolMessage:
        return ToolMessage(content=text, tool_call_id=f"a{n}", name="ask_docs")

    guard = RunGuardMiddleware({"ask_docs", "ask_chats", "ask_campus"})
    messages = [HumanMessage("сколько нужно заниматься физкультурой"), AIMessage(content="", tool_calls=[ask(1)]), report(1, core.TOOL_FAILURE_ANSWER)]
    assert guard._asked_again(types.SimpleNamespace(tool_call=ask(2), state={"messages": messages})) is None  # (the first one failed)
    messages += [AIMessage(content="", tool_calls=[ask(2)]), report(2, "2 часа в неделю [m1]."), AIMessage(content="", tool_calls=[ask(3)])]
    refused = guard._asked_again(types.SimpleNamespace(tool_call=ask(3), state={"messages": messages}))
    assert_test(LLMTestCase(input="", actual_output=str(refused.content)), [ContainsAll(["not asked again"], name="AskedHint")])
    assert guard._asked_again(types.SimpleNamespace(tool_call=ask(4, "ask_chats"), state={"messages": messages})) is None
    req = Req(0)
    req.messages = [*messages, refused]
    assert guard._final(req).tool_choice == "none"


def test_markup_on_a_call_without_tools_is_asked_again_with_why_it_was_not_made():
    """Forced to report, the docs helper wrote a third read as text; asked the same again it wrote the same (the server's
    cache), and the report was TOOL_FAILURE_ANSWER. Its markup and the reason go after the conversation, the start stays."""
    markup = AIMessage(content="<tool_call>\n<function=search_chats>\n<parameter=queries>[\"мидтерм итп\"]</parameter>\n</function>\n</tool_call>")
    report = AIMessage(content="Мидтерм в среду [m1].")
    seen = []
    before = Req(core.settings.agent_max_model_calls - 1)
    result = RunGuardMiddleware().wrap_model_call(before, lambda request: seen.append(request) or ModelResponse(result=[markup if len(seen) == 1 else report]))
    assert result.result[-1] is report
    assert seen[1].messages[: len(seen[0].messages)] == seen[0].messages and seen[1].tool_choice == "none"
    assert seen[1].messages[-2].content == markup.content
    assert_test(LLMTestCase(input="", actual_output=str(seen[1].messages[-1].content)), [ContainsAll(["was not made"], name="WhyNotMade")])


def test_after_a_call_that_only_repeated_earlier_ones_the_next_is_the_report():
    """The chats helper repeated its one search four times, each refused ('что писали в чатах про физкультуру для
    первокурсников?'): it had nothing new to look for. A call with one new search among the repeats goes on."""
    import json

    first, again, other = {**SEARCH, "id": "a"}, {**SEARCH, "id": "b"}, {**SEARCH, "args": {"queries": ["спорт"]}, "id": "c"}
    refused = ToolMessage(content=json.dumps({"error": core.DUPLICATE_HINT}), name="search_chats", tool_call_id="b")
    guard = RunGuardMiddleware({"search_chats"})
    req = Req(0)
    req.messages = [HumanMessage("физкультура"), AIMessage(content="", tool_calls=[first]), ToolMessage(content='{"total": 3}', name="search_chats", tool_call_id="a")]
    assert guard._final(req).tool_choice is None
    req.messages += [AIMessage(content="", tool_calls=[again]), refused]
    assert guard._final(req).tool_choice == "none"
    req.messages[-2:] = [AIMessage(content="", tool_calls=[again, other]), refused, ToolMessage(content='{"total": 2}', name="search_chats", tool_call_id="c")]
    assert guard._final(req).tool_choice is None


def test_a_repeated_tool_call_is_not_executed_again():
    first = {**SEARCH, "id": "a"}
    again = {**SEARCH, "id": "b"}
    messages = [HumanMessage("q"), AIMessage(content="", tool_calls=[first]), ToolMessage(content="{}", name="search_chats", tool_call_id="a"), AIMessage(content="", tool_calls=[again])]
    guard = RunGuardMiddleware()
    state = {"messages": messages}
    assert guard._duplicate(types.SimpleNamespace(tool_call=first, state=state)) is None  # the first one runs
    hint = guard._duplicate(types.SimpleNamespace(tool_call=again, state=state))
    assert_test(LLMTestCase(input="", actual_output=str(hint.content)), [ContainsAll(["already made"], name="DuplicateHint")])


def test_a_tool_call_written_as_text_is_repaired_or_never_shown():
    markup = AIMessage(content='<tool_call>\n<function=search_chats>\n<parameter=queries>["мидтерм итп"]</parameter>\n</function>\n</tool_call>')  # Qwen's format
    guard = RunGuardMiddleware()
    repaired, ok = guard._check(ModelResponse(result=[markup]), allow_calls=True)
    assert ok and guard._last(repaired).tool_calls[0]["name"] == "search_chats"
    _, ok = guard._check(ModelResponse(result=[markup]), allow_calls=False)  # no tools left: it cannot become a call
    assert not ok
