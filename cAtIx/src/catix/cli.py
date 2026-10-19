"""Usage: `catix "вопрос"` for a single answer, or `catix` for an interactive chat."""

import sys
import uuid

from langchain_core.messages import AIMessage

from catix.agent import tracing
from catix.agent.core import build_agent, final_answer
from catix.agent.tools import AgentContext


def ask(agent, question: str, thread_id: str) -> str:
    config = tracing.run_config(thread_id)
    context = AgentContext()
    for update in agent.stream({"messages": [{"role": "user", "content": question}]}, config, context=context, stream_mode="updates"):
        for step in update.values():
            for message in (step or {}).get("messages", []):
                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        print(f"  → {call['name']}({call['args']})", file=sys.stderr)
    return final_answer(agent.get_state(config).values["messages"], context.sources)


def main() -> None:
    agent = build_agent()
    thread_id = str(uuid.uuid4())
    if len(sys.argv) > 1:
        print(ask(agent, " ".join(sys.argv[1:]), thread_id))
        tracing.flush()
        return

    print("Ask a question (Ctrl+D to exit).")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            tracing.flush()
            return
        if question:
            print(ask(agent, question, thread_id), end="\n\n")
