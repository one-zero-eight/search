"""Shared pieces of the test suite: the local model as DeepEval judge, a way to ask the real agent, small metrics."""

import os
import random
import re
import uuid
from dataclasses import dataclass

# DeepEval and DeepTeam send telemetry to third parties unless told not to; the prompts under test stay on this machine.
os.environ["PHOENIX_PROJECT"] = "catix-tests"  # the traces of the tests go to their own Phoenix project, not among the real ones

for _key in ("DEEPTEAM_TELEMETRY_OPT_OUT", "DEEPEVAL_TELEMETRY_OPT_OUT", "TELEMETRY_OPT_OUT", "DEEPEVAL_UPDATE_WARNING_OPT_OUT"):
    os.environ[_key] = "YES"

from deepeval.metrics import BaseMetric  # noqa: E402
from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from deepeval.test_case import LLMTestCase  # noqa: E402
from langchain_core.messages import ToolMessage  # noqa: E402
from openai import LengthFinishReasonError  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

from catix.agent import tracing  # noqa: E402
from catix.agent.core import final_answer  # noqa: E402
from catix.agent.tools import AgentContext  # noqa: E402
from catix.settings import settings  # noqa: E402


class LocalModel(DeepEvalBaseLLM):
    """The model the bots use (llama.cpp, OpenAI-compatible) as judge and attacker; JSON outputs via json_schema."""

    def __init__(self, temperature: float = 0.0) -> None:
        self.chat = ChatOpenAI(
            base_url=str(settings.llm_route),
            api_key="not-needed",
            model=settings.llm_model,
            max_tokens=2000,
            temperature=temperature,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )

    def load_model(self):
        return self.chat

    # A small model sometimes runs on inside a structured answer until the token limit and the JSON is cut off: ask again.
    ATTEMPTS = 3

    def generate(self, prompt: str, schema=None):
        if schema is None:
            return self.chat.invoke(prompt).content
        for attempt in range(self.ATTEMPTS):
            try:
                return self.chat.with_structured_output(schema, method="json_schema").invoke(prompt)
            except LengthFinishReasonError:
                if attempt == self.ATTEMPTS - 1:
                    raise

    async def a_generate(self, prompt: str, schema=None):
        if schema is None:
            return (await self.chat.ainvoke(prompt)).content
        for attempt in range(self.ATTEMPTS):
            try:
                return await self.chat.with_structured_output(schema, method="json_schema").ainvoke(prompt)
            except LengthFinishReasonError:
                if attempt == self.ATTEMPTS - 1:
                    raise

    def get_model_name(self) -> str:
        return settings.llm_model


TEST_USER_BASE = 10**15  # ids far above any real one: `max:1000000000000123`; conftest deletes their abuse rows afterwards


def fresh_user() -> int:
    """A new negative (Max-style) id for every question: the guardrail counts attacks per user, and one user asking
    attack after attack in the tests would be paused."""
    return -(TEST_USER_BASE + random.randrange(10**12))


@dataclass
class Answer:
    text: str  # what the user sees, with the source list
    body: str  # the same without the source list
    tool_results: list[str]  # what the tools returned: the context the answer must be based on
    tool_names: list[str]


def ask(agent, question: str, user_id: int | None = None, only_chats: set[int] | None = None) -> Answer:
    """One question to the real agent as an ordinary user (not the owner of the InNoHassle token).
    `only_chats` limits the search to those chats, so that real chats cannot mix into a test about given messages."""
    user_id = fresh_user() if user_id is None else user_id
    out = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        tracing.run_config(uuid.uuid4().hex, str(user_id), name="test"),
        context=AgentContext(allowed_chat_ids=None if only_chats is None else frozenset(only_chats), user_telegram_id=user_id),
    )
    text = final_answer(out["messages"], out.get("sources") or {}) or ""
    messages = out["messages"]
    return Answer(
        text=text,
        body=re.split(r"\n\n(?:Источники|Sources):", text)[0].replace("*", ""),  # without markdown emphasis
        tool_results=[str(m.content) for m in messages if isinstance(m, ToolMessage)],
        tool_names=[c["name"] for m in messages for c in getattr(m, "tool_calls", None) or []],
    )


class _Deterministic(BaseMetric):
    """A metric that needs no model: subclasses implement `check`, which returns (passed, reason)."""

    name = "deterministic"

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.async_mode = False
        self.evaluation_model = "none"

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        raise NotImplementedError

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        passed, self.reason = self.check(test_case)
        self.score = 1.0 if passed else 0.0
        self.success = passed
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self) -> str:  # type: ignore[override]
        return self.name


class ContainsNone(_Deterministic):
    """The answer must not contain any of the given strings (case-insensitive)."""

    def __init__(self, forbidden: list[str], name: str = "ContainsNone", threshold: float = 1.0) -> None:
        super().__init__(threshold)  # every __init__ takes `threshold`: DeepEval rebuilds a metric from its attributes
        self.forbidden, self.name = forbidden, name

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        found = [f for f in self.forbidden if f.lower() in (test_case.actual_output or "").lower()]
        return not found, f"found: {found}" if found else "none of the forbidden strings"


class ContainsAll(_Deterministic):
    """The answer must contain every given string (case-insensitive)."""

    def __init__(self, required: list[str], name: str = "ContainsAll", threshold: float = 1.0) -> None:
        super().__init__(threshold)
        self.required, self.name = required, name

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        missing = [r for r in self.required if r.lower() not in (test_case.actual_output or "").lower()]
        return not missing, f"missing: {missing}" if missing else "all present"


class LatinShare(_Deterministic):
    """The share of Latin letters in the answer: about 1.0 for an English answer, about 0 for a Russian one."""

    def __init__(self, at_least: float | None = None, at_most: float | None = None, name: str = "LatinShare", threshold: float = 1.0) -> None:
        super().__init__(threshold)
        self.at_least, self.at_most, self.name = at_least, at_most, name

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        letters = [c for c in (test_case.actual_output or "") if c.isalpha()]
        share = sum(c.isascii() for c in letters) / max(1, len(letters))
        ok = (self.at_least is None or share >= self.at_least) and (self.at_most is None or share <= self.at_most)
        return ok, f"latin share {share:.0%}"


class SameLabel(_Deterministic):
    """The actual output must equal the expected one (a class label)."""

    name = "SameLabel"

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        return test_case.actual_output == test_case.expected_output, f"{test_case.actual_output!r} != {test_case.expected_output!r}"


class NoOtherDates(_Deterministic):
    """Every calendar date the answer mentions ("19 октября", "19.10") must be one of the allowed days."""

    MONTHS = "января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"

    def __init__(self, allowed: list[tuple[int, int]], name: str = "NoOtherDates", threshold: float = 1.0) -> None:
        super().__init__(threshold)
        self.allowed, self.name = allowed, name  # (day, month) pairs

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        text = (test_case.actual_output or "").lower()
        months = self.MONTHS.split("|")
        mentioned = {(int(d), months.index(m) + 1) for d, m in re.findall(rf"(\d{{1,2}})\s+({self.MONTHS})", text)}
        mentioned |= {(int(d), int(m)) for d, m in re.findall(r"(?<![\d.:])(\d{1,2})\.(\d{2})(?![\d:])", text) if 1 <= int(m) <= 12}
        extra = sorted(mentioned - set(self.allowed))
        return not extra, f"dates not in the messages: {extra}" if extra else "only the allowed dates"


class NoMatch(_Deterministic):
    """No regular expression of the list may match the answer (case-insensitive)."""

    def __init__(self, patterns: list[str], name: str = "NoMatch", threshold: float = 1.0) -> None:
        super().__init__(threshold)
        self.patterns, self.name = patterns, name

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        hits = [p for p in self.patterns if re.search(p, test_case.actual_output or "", re.I)]
        return not hits, f"matched: {hits}" if hits else "no pattern matched"


class MatchesAny(_Deterministic):
    """At least one regular expression of the list must match the answer (case-insensitive): the same fact written
    in different ways, e.g. "22 октября" or "22.10"."""

    def __init__(self, patterns: list[str], name: str = "MatchesAny", threshold: float = 1.0) -> None:
        super().__init__(threshold)
        self.patterns, self.name = patterns, name

    def check(self, test_case: LLMTestCase) -> tuple[bool, str]:
        hit = any(re.search(p, test_case.actual_output or "", re.I) for p in self.patterns)
        return hit, "matched" if hit else f"none of {self.patterns} matched"
