import asyncio

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from src.api.logging_ import logger
from src.config import settings

from .prompt import build_prompt

client = AsyncOpenAI(
    api_key=settings.ml_service.openrouter_api_key.get_secret_value(),
    base_url=settings.ml_service.llm_api_base,
)


async def generate_answer(
    question: str,
    contexts: list[str],
    lang_name: str | None = None,
) -> str:
    prompt = build_prompt(
        question,
        contexts,
        lang_name,
    )
    messages = [
        ChatCompletionSystemMessageParam(role="system", content=settings.ml_service.system_prompt),
        ChatCompletionUserMessageParam(role="user", content=prompt),
    ]

    logger.info(f"system prompt: {messages[0]['content']}")
    logger.info(f"user prompt: {messages[1]['content']}")

    resp = await client.chat.completions.create(
        model=settings.ml_service.llm_model,
        messages=messages,
        max_tokens=2048,
        temperature=0.4,
        top_p=1.0,
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    system = """
    You are a helpful multilingual assistant.
    Your ONLY rule is: ALWAYS answer in the SAME language as the input question.
    If the user writes in Russian — answer in Russian.
    If the user writes in English — answer in English. Etc.
    Examples:
    Q: Яндекс является резидентом Иннополиса?
    A: Да, Яндекс является резидентом в Иннополисе.

    Q: Is Yandex a resident of Innopolis?
    A: Yes, Yandex is a resident in Innopolis.

    Do not explain your behavior.
    Do not translate the question.
    Do not ask what language it is.

    Just answer in the same language as the input. """

    contexts = [
        "3 600 rubles, One room suite, 21 м², • 2 single beds, • Working area , • Mini kitchen, Designed to accommodate two guests",
        "4 400 rubles, Two-room Suite, 45 м², • 2 single beds, • Working area, • Lounge with Mini kitchen, • A TV, • An armchair and a sofa, Designed to accommodate two guests",
    ]
    question = "How much does a room for 2 people cost?"
    # r = asyncio.run(generate_answer("question", ["context 1", "context 2"]))
    # print(r)

    answer = asyncio.run(generate_answer(question, contexts))
    print(answer)
