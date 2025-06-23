from openai import OpenAI

from src.ml_service.config import settings

openai_client = OpenAI(api_key=settings.openai.api_key)


def generate_rag_answer(query, context_chunks):
    prompt = f"User's question: {query}\n\n" "Context:\n" + "\n".join(
        f"{i+1}. {chunk['text']}" for i, chunk in enumerate(context_chunks)
    )

    #
    #
    # Answer on user query based on context:
    # <query>Когда уборка во втором корпусе?</query>
    # <context>
    # <article id=1 url="">...</article>
    # </context>

    # Вы можете найти зуева в кабинете <map url="...">404</map>

    completion = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Ask the user's question based on the context provided."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
    )
    return completion.choices[0].message.content
