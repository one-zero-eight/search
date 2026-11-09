"""Real supervisor/helper graphs: only an explicit final retrieval report is public."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from langchain.tools import ToolRuntime
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from langgraph.types import Command
from pydantic import Field

from catix.agent import core
from catix.agent.tools import AgentContext

QUESTION = "When is the exam?"
FIRST = "The exam takes place tomorrow [m0]. "
LAST = "Bring your student card [m0]."


def call(name, ident, **args):
    return AIMessage("", tool_calls=[{"name": name, "id": ident, "args": args}])


class TokenModel(BaseChatModel):
    """A real chat model with controllable token boundaries, not a forwarding mock."""

    steps: list = Field(default_factory=list)
    cursor: list[int] = Field(default_factory=lambda: [0])
    choices: list = Field(default_factory=list)
    gate: object = None
    last_token: object = None
    cancelled: bool = False

    @property
    def _llm_type(self):
        return "helper-answer-token-fixture"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        return self.bind(tools=tools, tool_choice=tool_choice, **kwargs)

    def _next(self, kwargs):
        self.choices.append(kwargs.get("tool_choice"))
        index = self.cursor[0]
        self.cursor[0] += 1
        assert index < len(self.steps), "Unexpected extra model call"
        return self.steps[index]

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        step = self._next(kwargs)
        message = step if isinstance(step, AIMessage) else AIMessage("".join(c.text for c in step))
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        step = self._next(kwargs)
        chunks = ([AIMessageChunk(content=step.content, tool_calls=step.tool_calls)]
                  if isinstance(step, AIMessage) else step)
        for index, chunk in enumerate(chunks):
            if index == len(chunks) - 1 and len(chunks) > 1:
                if self.gate is not None:
                    assert self.gate.wait(10), "Test did not release the final model token"
                if self.cancelled:
                    raise GraphBubbleUp("Synthetic generation cancellation")
                if self.last_token is not None:
                    self.last_token.set()
            yield ChatGenerationChunk(message=chunk)


@pytest.fixture
def retrieval(monkeypatch):
    @tool("search_chats")
    def search(queries: list[str], runtime: ToolRuntime[AgentContext]) -> Command:
        """Read deterministic current-turn evidence."""
        return Command(update={
            "messages": [ToolMessage(content='{"results":[{"ref":"m0","text":"The exam takes place tomorrow. Bring your student card."}]}',
                                     name="search_chats", tool_call_id=runtime.tool_call_id,
                                     artifact={"relevant": ["m0"]})],
            "sources": {"m0": {"wiki": True, "title": "Exam notice", "link": None, "trust": "official"}},
        })

    monkeypatch.setattr(core, "TOOLS", [search])
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(core.settings, "agent_pass_report", True)
    monkeypatch.setattr(core.settings, "agent_max_model_calls", 3)


def script(*reports):
    return [call("ask_chats", "helper", question=QUESTION),
            call("search_chats", "search-1", queries=["exam"]),
            call("search_chats", "search-2", queries=["exam tomorrow"]),
            *reports]


def collect(model, *, context=None, inputs=None):
    graph = core.build_agent(model, guardrail=False)
    events = list(graph.stream(inputs or {"messages": [HumanMessage(QUESTION)]},
                               {"configurable": {"thread_id": "helper-stream"}},
                               context=context or AgentContext(), stream_mode=["custom", "values"]))
    answers = [data["answer_stream"] for mode, data in events if mode == "custom" and "answer_stream" in data]
    values = [data for mode, data in events if mode == "values"]
    return answers, values[-1]


def test_final_answer_is_delivered_before_last_token_and_graph_completion(retrieval):
    gate, last_token, completed = Event(), Event(), Event()
    model = TokenModel(steps=script([AIMessageChunk(content=FIRST), AIMessageChunk(content=LAST)]),
                       gate=gate, last_token=last_token)
    graph = core.build_agent(model, guardrail=False)
    first_answer = Event()
    observed = []

    def consume():
        try:
            for mode, data in graph.stream({"messages": [HumanMessage(QUESTION)]},
                                           {"configurable": {"thread_id": "incremental-helper"}},
                                           context=AgentContext(), stream_mode=["custom", "values"]):
                if mode == "custom" and "answer_stream" in data:
                    observed.append(data["answer_stream"])
                    first_answer.set()
        finally:
            completed.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(consume)
        try:
            assert first_answer.wait(5), "No answer until the held final token"
            assert not last_token.is_set()
            assert not completed.is_set()
            assert observed == [{"id": "helper", "text": FIRST.strip()}]
        finally:
            gate.set()
        future.result(timeout=10)
    assert last_token.is_set() and completed.is_set()
    assert model.cursor == [4], "The pass-report optimization must not add a supervisor rewrite"
    assert model.choices[-1] == "none"
    assert model.callbacks is None, "The shared model must not retain invocation callbacks"


@pytest.mark.parametrize("case", ["disabled", "multiple", "direct", "optional", "stale"])
def test_ineligible_helper_text_stays_private(retrieval, monkeypatch, case):
    steps = script([AIMessageChunk(content=FIRST), AIMessageChunk(content=LAST)])
    inputs = None
    context = AgentContext()
    if case == "disabled":
        monkeypatch.setattr(core.settings, "agent_pass_report", False)
    if case == "optional":
        steps.pop(2)
    if case in {"multiple", "direct"}:
        earlier = call("ask_docs" if case == "multiple" else "search_api_tools", "earlier", question=QUESTION)
        inputs = {"messages": [HumanMessage(QUESTION), earlier,
                               ToolMessage("No result", name=earlier.tool_calls[0]["name"], tool_call_id="earlier")]}
    if case == "stale":
        steps = [call("ask_chats", "helper", question=QUESTION),
                 AIMessage("No current retrieval [m9]."), AIMessage("No confirmed information.")]
        inputs = {"messages": [HumanMessage(QUESTION)],
                  "sources": {"m9": {"wiki": True, "title": "Previous turn", "link": None, "trust": "official"}}}
    else:
        steps.append(AIMessage("The exam takes place tomorrow [m0]."))
    answers, output = collect(TokenModel(steps=steps), context=context, inputs=inputs)
    assert answers == []
    assert output["messages"][-1].type == "ai"


@pytest.mark.parametrize("invalid", ["uncited", "language", "markup", "unknown_ref"])
def test_rejected_attempt_is_reset_before_repair_or_synthesis(retrieval, invalid):
    final = {"uncited": "Bring your student card.",
             "language": "Завтра экзамен. " * 30,
             "markup": "<tool_call><function=search_chats></function></tool_call>",
             "unknown_ref": "Bring your student card [m9]."}[invalid]
    first = FIRST if invalid != "uncited" else "The exam takes place tomorrow. "
    if invalid == "unknown_ref":
        first = first.replace("m0", "m9")
    steps = script([AIMessageChunk(content=first), AIMessageChunk(content=final)])
    if invalid in {"uncited", "markup"}:
        steps.append([AIMessageChunk(content=FIRST), AIMessageChunk(content=LAST)])
    if invalid in {"language", "unknown_ref"}:
        steps.append(AIMessage("No confirmed information."))
    answers, _ = collect(TokenModel(steps=steps))
    assert answers[0]["text"]
    reset = answers.index({"id": "helper", "reset": True})
    assert reset > 0
    if invalid == "unknown_ref":
        assert all("m9" not in answer.get("text", "") for answer in answers)


def test_partial_answer_is_cleaned_against_current_evidence(retrieval):
    chunks = [AIMessageChunk(content=[{"type": "reasoning", "reasoning": "PRIVATE REASONING"}]),
              AIMessageChunk(content="The administration announced an official notice [m0]. "),
              AIMessageChunk(content="Read [the invented page](https://invented.invalid/exam) [m9]. "),
              AIMessageChunk(content=FIRST), AIMessageChunk(content=LAST)]
    answers, output = collect(TokenModel(steps=script(chunks)))
    assert answers
    for answer in answers:
        text = answer.get("text", "")
        assert "PRIVATE" not in text and "invented.invalid" not in text
        assert "administration announced" not in text and "[m9]" not in text
    assert output["messages"][-1].name == core.SUPERVISOR_NAME


def test_cancelled_generation_clears_partial_and_callback_scope(retrieval):
    gate = Event()
    gate.set()
    model = TokenModel(steps=script([AIMessageChunk(content=FIRST), AIMessageChunk(content=LAST)]),
                       gate=gate, cancelled=True)
    graph = core.build_agent(model, guardrail=False)
    events = []
    with pytest.raises(GraphBubbleUp, match="Synthetic generation cancellation"):
        for data in graph.stream({"messages": [HumanMessage(QUESTION)]},
                                  {"configurable": {"thread_id": "cancelled-helper"}},
                                  context=AgentContext(), stream_mode="custom"):
            if "answer_stream" in data:
                events.append(data["answer_stream"])
    assert events[-1] == {"id": "helper", "reset": True}
    assert core._HELPER_ANSWER_STREAM.get() is None
    assert model.callbacks is None


def test_concurrent_invocations_keep_callbacks_and_streams_separate(retrieval):
    def invoke(index):
        prefix = f"Exam number {index} takes place tomorrow [m0]. "
        model = TokenModel(steps=script([AIMessageChunk(content=prefix), AIMessageChunk(content=LAST)]))
        answers, output = collect(model)
        assert core._HELPER_ANSWER_STREAM.get() is None
        assert model.callbacks is None
        return answers, output

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, [1, 2]))
    for index, (answers, output) in enumerate(results, 1):
        assert answers[0]["text"] == f"Exam number {index} takes place tomorrow [m0]."
        assert str(index) in output["messages"][-1].text


def test_api_async_stream_delivers_real_helper_answer_before_last_model_token(retrieval, monkeypatch):
    import asyncio

    from catix.api import ask

    gate, last_token = Event(), Event()
    model = TokenModel(steps=script([AIMessageChunk(content=FIRST), AIMessageChunk(content=LAST)]),
                       gate=gate, last_token=last_token)
    graph = core.build_agent(model, guardrail=False)
    monkeypatch.setattr(ask, "agent", lambda: graph)

    async def consume():
        queue = asyncio.Queue()
        task = asyncio.create_task(ask.stream_agent(
            {"messages": [HumanMessage(QUESTION)]},
            {"configurable": {"thread_id": "async-helper-stream"}}, AgentContext(), queue))
        try:
            async def first_answer():
                while True:
                    kind, payload = await queue.get()
                    if kind == "answer":
                        return payload["text"]

            text = await asyncio.wait_for(first_answer(), 5)
            assert "The exam takes place tomorrow" in text
            assert "[m0]" not in text and "Bring your student card" not in text
            assert not last_token.is_set()
            assert not task.done()
        finally:
            gate.set()
        output = await asyncio.wait_for(task, 10)
        assert last_token.is_set()
        assert output["messages"][-1].name == core.SUPERVISOR_NAME
        assert output["messages"][-1].text == FIRST + LAST
        assert core.final_answer(output["messages"], output["sources"]).sources[0].title == "Exam notice"
        assert model.cursor == [4], "No additional supervisor model invocation"
        assert model.callbacks is None

    asyncio.run(consume())
