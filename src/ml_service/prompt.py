from string import Template

TEMPLATE = Template(
    """${system_prompt}

${contexts}

Question: ${question}

Answer:"""
)


def build_prompt(
    question: str,
    contexts: list[str],
    system_prompt: str,
) -> str:
    ctx = "\n\n".join(f"- {c}" for c in contexts)
    return TEMPLATE.substitute(
        system_prompt=system_prompt.strip(),
        contexts=ctx,
        question=question.strip(),
    )


if __name__ == "__main__":
    print(build_prompt("question", ["context 1", "context 2"], "system prompt"))
