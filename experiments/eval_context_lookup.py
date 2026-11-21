"""Does the supervisor look a factual question up again when the conversation already holds an answer to it?

Replays a conversation history into the real supervisor (`build_agent(guardrail=False)`: its real prompt, tool schemas and
middleware stack) and stops it right after its FIRST model step (`interrupt_before=["tools"]`, so no helper, database or
embedder runs). A run counts as a lookup when that step holds a tool call. The same cases run with two texts of the
supervisor prompt, in the same process: BASELINE is `roles.SUPERVISOR` of a git revision (default HEAD) and NEW is the
working tree. Sampling is random (PlanThinkingMiddleware: temperature 0.85, thinking), hence N runs per case.

Cases: the failing contexts of trace 7fb329d3 (the same question repeated after a negative answer; its thread is read from
the Postgres checkpointer, `--no-real` leaves it out), the "перечисли все виды" follow-up of chat 31428eb9 and variants of it, a
long mixed history, a follow-up the old report cannot answer, and controls that must NOT call a tool (a greeting, thanks,
"what can you do", an under-specified request, an off-topic task). The guardrail screen is off, so the controls test the prompt alone.

Usage: uv run python experiments/eval_context_lookup.py [--reps N] [--only 1,2,C1] [--baseline REF] [--parallel K] [--no-real] [--dry]
       uv run python experiments/eval_context_lookup.py --report RUNS.jsonl...   (the tables of raw runs, no model calls)
The model server may scale to zero (Modal): the first request waits for a cold start, hence the warm-up. Raw runs: --out (jsonl).
"""

import argparse
import asyncio
import collections
import difflib
import itertools
import json
import math
import os
import subprocess
import sys
import time
import types
import uuid
from dataclasses import dataclass, field

os.environ.setdefault("PHOENIX_PROJECT", "catix-eval")  # before the import of catix: the traces of this experiment stay apart

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from catix.agent import roles, tracing
from catix.agent.core import SUPERVISOR_NAME, build_agent
from catix.agent.tools import AgentContext
from catix.settings import settings

# --- histories: the real texts of the traces, shortened where they were long ---

_ids = itertools.count(1)


def turn(question: str, answer: str, helper: tuple[str, dict, str] | None = None) -> list[BaseMessage]:
    """One earlier question of the conversation as the checkpointer keeps it: the question, the supervisor's call of a
    helper or an API tool with its result (`helper` = tool, arguments, result), and the supervisor's answer."""
    messages: list[BaseMessage] = [HumanMessage(question)]
    if helper:
        tool, args, result = helper
        call_id = f"chatcmpl-tool-{next(_ids):016x}"
        messages += [AIMessage("", name=SUPERVISOR_NAME, tool_calls=[{"name": tool, "args": args, "id": call_id, "type": "tool_call"}]),
                     ToolMessage(result, tool_call_id=call_id, name=tool)]
    return [*messages, AIMessage(answer, name=SUPERVISOR_NAME)]


def docs(question: str, report: str, answer: str | None = None, *, asked: str | None = None) -> list[BaseMessage]:
    """A question answered by the docs helper; the supervisor passes the report on as it is (PassReportMiddleware)."""
    return turn(question, answer or report, ("ask_docs", {"question": asked or question}, report))


# Trace e648e913, thread api:31428eb9: the report of the docs helper on "есть ли особые стипендии для студентов?"
STIPENDS = """В Университете Иннополис применяется несколько видов стипендий, включая особые формы поощрения за выдающиеся достижения [m0][m7]. Основные типы:

*   **Государственные стипендии:** государственная академическая стипендия (за успехи в учёбе), повышенная государственная академическая стипендия (за особые достижения в одной или нескольких областях: учебной, научно-исследовательской, общественно-значимой, культурно-творческой и спортивной) [m0][m3], государственная социальная стипендия [m0].
*   **Стипендии Президента и Правительства РФ:** предусмотрены как отдельный вид поддержки [m0].
*   **Стипендии Университета (уникальные формы):**
    *   **Повышенная стипендия Университета:** назначается за особые достижения в какой-либо области деятельности (учебной, научно-исследовательской, общественной, культурно-творческой и спортивной). Может быть назначена всем студентам [m6]. Критерии включают индивидуальные достижения до поступления, успехи в научных работах и публикациях, участие во внешних олимпиадах и программах академической мобильности, активно…
    *   **Академическая стипендия АНО ВО «Университет Иннополис»** и **повышенная академическая стипендия** (за особые успехи в учебной деятельности) [m7].
    *   **Именные стипендии** (предоставляются юридическими или физическими лицами) [m7].

Подробные условия назначения и размеры указаны в Приказе о Положении о стипендиях и иных формах материальной поддержки студентов и аспирантов (от 28.05.2025) и связанных приказах об установлении размеров [m0][m5]."""
STIPEND_TURN = docs("есть ли особые стипендии для студентов?", STIPENDS, asked="есть ли особые стипендии для студентов")

# Trace 7fb329d3: a negative answer, then other questions, then the same question again.
NO_MOSCHANETSKY = ("В документах и базах знаний Университета Иннополис не найдено информации о преподавателе по фамилии Мощанецкий "
                   "или «мощанецкий университет». В найденных материалах указаны другие сотрудники университета: ректор Евгений Бобров [m16], "
                   "директор Дмитрий Вандюков [m19], декан факультета компьютерных и инженерных наук Мануэль Маццара [m17].")
KUDASOV = ("В документах Университета Иннополис нет упоминаний учреждения «Кудасов университет». В найденных материалах встречается "
           "только **Кудасов Николай Дмитриевич** — доцент Центра образовательных программ топ-уровня в сфере искусственного интеллекта "
           "Университета Иннополис [m0][m1][m2]. Он преподаёт курсы «Алгоритмы и структуры данных», «Логика решения задач» [m3][m4].")
BASKAKOV = ("Баскаков Анатолий Евгеньевич — ассистент Университета Иннополис, работает в лаборатории программной инженерии [m27][m28].\n\n"
            "Он преподавал следующие курсы (в разных наборах):\n- **Математический анализ** (09.03.01 Информатика и вычислительная "
            "техника, наборы 2024–2025 гг.) [m21][m22][m24]\n- **Математический анализ II** (набор 2024) [m23]")
CAPABILITIES = ("Я помогаю студентам и сотрудникам Университета Иннополис:\n\n**Расписание и календарь** — читаю ваше личное расписание "
                "(занятия, спорт, забронированные комнаты), добавляю и удаляю события в ваш календарь.\n\n**Moodle** — показываю дедлайны, "
                "оценки, объявления по курсам, ищу материалы в файлах курсов.\n\n**Университетские данные** — расписания групп, курсы и "
                "преподаватели этого семестра, свободные комнаты, клубы, мероприятия; правила и документы; объявления из чатов.")

MOSCHANETSKY_HISTORY = [
    *turn("что такое квантовая залупность", "Такого термина не существует — это бессмысленное выражение без научного или образовательного значения.\n\n"
          "Можете задать вопрос о реальных направлениях: курсы, расписание, правила университета, документы или мои функции для помощи студентам Innopolis."),
    *docs("кто такой кудасов", KUDASOV, asked="кто такой кудасов университет innopolis"),
    *docs("кто такой мощанецкий", NO_MOSCHANETSKY, asked="кто такой мощанецкий университет innopolis преподаватель"),
    *turn("найди самое часто повторяющееся слово в документах инополиса",
          "Я не могу выполнить этот запрос — мои инструменты позволяют искать конкретную информацию в документах (правила, процедуры, факты, "
          "новости), но не проводить статистический анализ.\n\nЕсли нужна информация по конкретной теме — задайте вопрос, и я найду её через документы или чаты."),
    *turn("что ты умеешь", CAPABILITIES),
    *docs("баскаков кто это", BASKAKOV, asked="кто такой баскаков университет innopolis преподаватель"),
    *turn('добавь в час дня"', "«Добавь в час дня» — слишком кратко. Что именно и куда добавить?\n\nНапример: событие, мероприятие или занятие? На какой день?"),
]

# A midterm date from the chats that names no room.
MIDTERM_REPORT = ("Мидтерм по Computer Architecture (компарх) назначен на 3 декабря в 10:00 [m4]. О нём объявили в чате курса в понедельник; "
                  "аудитория в сообщениях не названа [m4][m5].")
MIDTERM_TURN = turn("когда мидтерм по компарху?", MIDTERM_REPORT, ("ask_chats", {"question": "когда мидтерм по компарху"}, MIDTERM_REPORT))

# Other topics, for the long history.
CLUBS = ('{"total": 2, "clubs": [{"title": "Chess Club", "description": "Weekly games and tournaments", "leader": "@chessinno"}, '
         '{"title": "Chess & Go", "description": "Board games evenings, Wednesdays", "leader": "@boardgames_inno"}]}')
CANTEEN = '{"total": 1, "areas": [{"title": "Столовая", "building": "Университет, 1 этаж", "floor": 1}]}'
RETAKES = ("Экзамен можно пересдавать до двух раз: первая пересдача проходит в течение двух недель после сессии, вторая — с комиссией [m2][m3]. "
           "Повторное прохождение дисциплины возможно на платной основе [m3].")
LEAVE = ("Академический отпуск предоставляется на срок до двух лет по медицинским показаниям или семейным обстоятельствам; "
         "заявление подаётся в учебный офис с подтверждающими документами [m8][m9].")
LONG_HISTORY = [
    *turn("привет", "Привет! Чем могу помочь?"),
    *turn("какие клубы по шахматам есть?", "Есть два шахматных клуба: **Chess Club** (еженедельные партии и турниры, @chessinno) и "
          "**Chess & Go** (вечера настольных игр по средам, @boardgames_inno).",
          ("call_api_tool", {"name": "clubs_get_clubs", "arguments": {"query": "chess"}}, CLUBS)),
    *STIPEND_TURN,
    *MIDTERM_TURN,
    *turn("где столовая?", "Столовая находится на 1 этаже главного корпуса.",
          ("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "canteen"}}, CANTEEN)),
    *turn("спасибо", "Пожалуйста!"),
    *docs("сколько раз можно пересдавать экзамен?", RETAKES, asked="сколько раз можно пересдавать экзамен"),
    *docs("а академ отпуск на сколько можно?", LEAVE, asked="на какой срок можно взять академический отпуск"),
]
LONG_HISTORY_WITHOUT_STIPENDS = [m for m in LONG_HISTORY if m not in STIPEND_TURN]


def real_thread(thread_id: str) -> list[BaseMessage]:
    """The conversation of a chat as the checkpointer keeps it: everything before the thread's LAST question."""
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(settings.database_url) as saver:
        found = saver.get_tuple({"configurable": {"thread_id": thread_id}})
    messages = found.checkpoint["channel_values"]["messages"]
    return messages[: max(i for i, m in enumerate(messages) if m.type == "human")]


@dataclass
class Case:
    id: str
    title: str
    question: str
    history: list[BaseMessage] | str = field(default_factory=list)  # a thread id: read from Postgres when the run starts
    expect: frozenset[str] = frozenset()  # tools that are the right lookup; empty: a control, any tool call is a regression
    note: str = ""


DOCS_OR_CHATS = frozenset({"ask_docs", "ask_chats"})
CASES = [
    Case("1", "repeat of a question answered negatively (7fb329-like)", "кто такой мощанецкий", MOSCHANETSKY_HISTORY, frozenset({"ask_docs"})),
    Case("2", "31428eb9 turn 2: «перечисли все виды»", "перечисли все виды", STIPEND_TURN, frozenset({"ask_docs"})),
    Case("3", "31428eb9: «ты уверен? откуда это?»", "ты уверен? откуда это?", STIPEND_TURN, DOCS_OR_CHATS, "a new lookup; or no new facts"),
    Case("4", "long history (28 messages) holding a scholarship answer", "есть ли особые стипендии за достижения студента?", LONG_HISTORY, frozenset({"ask_docs"})),
    Case("4b", "the same long history without the scholarship turn", "есть ли особые стипендии за достижения студента?",
         LONG_HISTORY_WITHOUT_STIPENDS, frozenset({"ask_docs"})),
    Case("5", "«и в какой аудитории?» after a midterm date without a room", "и в какой аудитории?", MIDTERM_TURN, DOCS_OR_CHATS, "the chats may name it"),
    Case("R1", "REAL 7fb329d3 thread (52 messages before the question), same question", "кто такой мощанецкий", "api:a7b30e0e510648aab275670d", frozenset({"ask_docs"})),
    Case("C1", "control: a greeting", "Привет!"),
    Case("C2", "control: thanks after an answer", "спасибо большое", STIPEND_TURN),
    Case("C3", "control: what can you do", "что ты умеешь?"),
    Case("C4", "control: under-specified action (one clarifying question)", "добавь в час дня"),
    Case("C5", "control: an off-topic task (a refusal)", "напиши функцию на python, которая сортирует список"),
]


def context() -> AgentContext:
    """The asker of the site, signed in: the supervisor has the same tools and prompt parts as in the trace of 7fb329d3."""
    return AgentContext(innohassle_token=SecretStr("eval"), innohassle_id="eval-context-lookup", study_group="B26-CSE-01",
                        verified_study_groups=("B26-CSE-01", "ESCP-3"), attachment_chat_id="eval-context-lookup")


# --- the two prompts ---


def baseline_prompt(ref: str) -> str:
    """`roles.SUPERVISOR` of a git revision, by running that revision's roles.py as a module of its own."""
    source = subprocess.run(["git", "show", f"{ref}:src/catix/agent/roles.py"], capture_output=True, text=True, check=True).stdout
    module = types.ModuleType("roles_baseline")
    exec(compile(source, f"roles.py@{ref}", "exec"), module.__dict__)
    return module.SUPERVISOR


class CountCalls(BaseCallbackHandler):
    """Counts the model calls of a run (the first step, retries of the guard, the summary of a long history)."""

    def __init__(self) -> None:
        self.calls = 0

    def on_chat_model_start(self, *args, **kwargs) -> None:
        self.calls += 1


async def run_once(agent, case: Case, history: list[BaseMessage], version: str, rep: int) -> dict:
    """One run: the history and the question; stops at the first tool call. What the first model step held."""
    counter = CountCalls()
    thread = f"eval-lookup-{uuid.uuid4().hex}"
    config = {**tracing.run_config(thread, "eval-context-lookup", name=f"{version}/{case.id}/{rep}"), "callbacks": [counter]}
    messages = [m.model_copy(update={"id": None}) for m in history] + [HumanMessage(case.question)]
    started = time.monotonic()
    row = {"case": case.id, "version": version, "rep": rep, "tools": [], "calls": [], "text": "", "error": None}
    for attempt in range(3):
        try:
            await asyncio.wait_for(agent.ainvoke({"messages": messages}, config, context=context(), interrupt_before=["tools"]), 600)
            state = await agent.aget_state(config)
            run = state.values["messages"]
            run = run[max(i for i, m in enumerate(run) if isinstance(m, HumanMessage)) + 1:]
            first = next(m for m in run if isinstance(m, AIMessage))
            row["calls"] = [{"name": c["name"], "args": c["args"]} for c in first.tool_calls]
            row["tools"] = [c["name"] for c in first.tool_calls]
            row["text"] = first.text.strip()
            row["error"] = None
            break
        except Exception as e:  # noqa: BLE001  a refused connection or a timeout of a model server that was starting
            row["error"] = f"{type(e).__name__}: {str(e)[:120]}"
            thread = f"eval-lookup-{uuid.uuid4().hex}"
            config["configurable"]["thread_id"] = thread
            await asyncio.sleep(5 * (attempt + 1))
    row.update(seconds=round(time.monotonic() - started, 1), model_calls=counter.calls)
    return row


async def warm_up() -> None:
    """The first request of a Modal server that scaled to zero waits for a cold start of a few minutes."""
    llm = ChatOpenAI(base_url=str(settings.llm_route), api_key=settings.llm_api_key, model=settings.llm_model, max_tokens=4, max_retries=0,
                     timeout=900, extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    started = time.monotonic()
    for attempt in range(48):  # 503 "no upstreams available" until the container is up
        try:
            await llm.ainvoke("ping")
            print(f"model server ready after {time.monotonic() - started:.0f}s", flush=True)
            return
        except Exception as e:  # noqa: BLE001
            print(f"  warm-up try {attempt + 1}: {type(e).__name__}: {str(e)[:100]}", flush=True)
            await asyncio.sleep(15)
    sys.exit("the model server does not answer")


def fisher_greater(a: int, an: int, b: int, bn: int) -> float:
    """One-sided Fisher exact p: the chance that `a` of `an` is as many above `b` of `bn` by luck alone."""
    total, hits = an + bn, a + b
    return sum(math.comb(hits, k) * math.comb(total - hits, an - k) for k in range(a, min(an, hits) + 1)) / math.comb(total, an)


def lookup(rows: list[dict], case: Case) -> tuple[int, int, int]:
    """(runs with a tool call, runs with an expected tool among the calls, runs counted); runs that failed are left out."""
    ok = [r for r in rows if not r["error"]]
    return sum(bool(r["tools"]) for r in ok), sum(bool(case.expect & set(r["tools"])) for r in ok), len(ok)


def report(cases: list[Case], rows: list[dict]) -> None:
    by = collections.defaultdict(list)
    for r in rows:
        by[r["case"], r["version"]].append(r)
    print("\n| case | expect | version | tool call | expected tool | tools in the first step | no tool: first words |")
    print("|---|---|---|---|---|---|---|")
    for case in cases:
        for version in ("baseline", "new"):
            rs = by[case.id, version]
            any_call, expected, n = lookup(rs, case)
            tools = collections.Counter(t for r in rs if not r["error"] for t in r["tools"])
            texts = [r["text"][:50].replace("\n", " ") for r in rs if not r["error"] and not r["tools"]]
            errors = sum(bool(r["error"]) for r in rs)
            print(f"| {case.id} | {'/'.join(sorted(case.expect)) or 'none (control)'} | {version} | {any_call}/{n} | "
                  f"{expected}/{n if case.expect else '-'} | {', '.join(f'{t}×{c}' for t, c in tools.most_common()) or '-'} | "
                  f"{' ¦ '.join(texts[:2])}{f' (errors: {errors})' if errors else ''} |")
    print("\nlookups (a tool call in the first step), baseline -> new; Fisher one-sided p that new calls more:")
    total = {"baseline": [0, 0], "new": [0, 0]}
    for case in cases:
        if not case.expect:
            continue
        (b, _, bn), (n, _, nn) = (lookup(by[case.id, v], case) for v in ("baseline", "new"))
        total["baseline"][0] += b; total["baseline"][1] += bn; total["new"][0] += n; total["new"][1] += nn
        print(f"  {case.id:>3}: {b}/{bn} -> {n}/{nn}   p={fisher_greater(n, nn, b, bn):.3f}   {case.title}")
    (b, bn), (n, nn) = total["baseline"], total["new"]
    print(f"  all lookup cases: {b}/{bn} -> {n}/{nn}   p={fisher_greater(n, nn, b, bn):.4f}")
    controls = [c for c in cases if not c.expect]
    if controls:
        print("controls with a tool call (regressions): " + ", ".join(
            f"{c.id} baseline {lookup(by[c.id, 'baseline'], c)[0]}/{lookup(by[c.id, 'baseline'], c)[2]} new {lookup(by[c.id, 'new'], c)[0]}/{lookup(by[c.id, 'new'], c)[2]}"
            for c in controls))
    print(f"model calls: {sum(r['model_calls'] for r in rows)} in {len(rows)} runs; errors: {sum(bool(r['error']) for r in rows)}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--reps", type=int, default=8, help="runs per case and prompt version")
    parser.add_argument("--only", help="comma-separated case ids")
    parser.add_argument("--baseline", default="HEAD", help="git revision whose roles.SUPERVISOR is the baseline")
    parser.add_argument("--parallel", type=int, default=8, help="requests at once (the Modal server takes 8)")
    parser.add_argument("--no-real", action="store_true", help="leave out the cases read from the Postgres checkpointer")
    parser.add_argument("--dry", action="store_true", help="no model calls: the histories and the difference of the prompts")
    parser.add_argument("--out", default=f"/tmp/eval_context_lookup_{time.strftime('%H%M%S')}.jsonl")
    parser.add_argument("--report", nargs="+", metavar="JSONL", help="no model calls: the tables of earlier raw runs (--out files)")
    args = parser.parse_args()
    if args.report:
        rows = [json.loads(line) for path in args.report for line in open(path)]
        report([c for c in CASES if c.id in {r["case"] for r in rows}], rows)
        return

    cases = [c for c in CASES if (not args.only or c.id in args.only.split(",")) and not (args.no_real and isinstance(c.history, str))]
    prompts = {"baseline": baseline_prompt(args.baseline), "new": roles.SUPERVISOR}
    if prompts["baseline"] == prompts["new"]:
        print(f"WARNING: roles.SUPERVISOR of the working tree equals that of {args.baseline}: nothing to compare")
    histories = {c.id: real_thread(c.history) if isinstance(c.history, str) else c.history for c in cases}

    if args.dry:
        print("".join(difflib.unified_diff(prompts["baseline"].splitlines(True), prompts["new"].splitlines(True), "baseline", "new")))
        for c in cases:
            h = histories[c.id]
            print(f"{c.id:>3}  {len(h):3d} messages, ~{count_tokens_approximately(h):5d} tokens  {c.title}")
        return

    agent = build_agent(guardrail=False)
    await warm_up()
    gate = asyncio.Semaphore(args.parallel)

    async def bounded(case: Case, version: str, rep: int) -> dict:
        async with gate:
            return await run_once(agent, case, histories[case.id], version, rep)

    rows: list[dict] = []
    for i, case in enumerate(cases):
        for version in (("baseline", "new") if i % 2 == 0 else ("new", "baseline")):  # the prompt is a module global: one version at a time
            roles.SUPERVISOR = prompts[version]
            batch = await asyncio.gather(*(bounded(case, version, rep) for rep in range(args.reps)))
            rows += batch
            with open(args.out, "a") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in batch)
            n = sum(bool(r["tools"]) for r in batch if not r["error"])
            print(f"[{case.id:>3} {version:8s}] tool call {n}/{len(batch)}  {collections.Counter(t for r in batch for t in r['tools']).most_common()}"
                  f"  errors {sum(bool(r['error']) for r in batch)}  {max(r['seconds'] for r in batch):.0f}s", flush=True)
    roles.SUPERVISOR = prompts["new"]
    report(cases, rows)
    print(f"raw runs: {args.out}")
    if tracing.enabled():
        tracing._provider.force_flush()


if __name__ == "__main__":
    asyncio.run(main())
