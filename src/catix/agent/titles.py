"""The name of a chat of the site's assistant, for the list of the user's chats (GET /ask/chats): a few words on what the
first question is about, from one more short call of the model. It runs while the agent answers that question
(api/ask.py), so the answer does not wait for it; until it comes, and when it fails, the chat is named by the question.
"""

from langchain_openai import ChatOpenAI

from catix.agent import tracing
from catix.agent.core import _language
from catix.settings import settings

MAX_CHARS = 80  # a name longer than this is cut
QUESTION_CHARS = 1000  # of the question the model reads

PROMPT = """\
Name a conversation with a university assistant that starts with the question below: 2 to 6 words on its topic, in \
{language}, as a title and not as a question. No quotes, no full stop at the end, no emoji. Reply with the name only.

Question:
{question}
"""


def _model() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=str(settings.llm_route),
        api_key="not-needed",
        model=settings.llm_model,
        max_tokens=30,
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def clean(text: str) -> str | None:
    """The name from what the model wrote: its first line without quotes and a full stop; None when nothing is left."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return None
    name = lines[0].removeprefix("Title:").removeprefix("Название:").strip().strip("\"'«»“”„*`").strip().rstrip(".").strip()
    return name[:MAX_CHARS].strip() or None


def name(question: str) -> str | None:
    """The name of a chat that starts with this question, or None when the model gave none."""
    # The language is decided in code, as for the agent's answers: the model kept English for some Russian questions.
    prompt = PROMPT.format(language=_language(question), question=question.strip()[:QUESTION_CHARS])
    reply = _model().invoke(prompt, config=tracing.run_config("chat-title", name="chat-title"))
    return clean(reply.text)
