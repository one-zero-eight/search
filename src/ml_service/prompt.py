from string import Template

TEMPLATE = Template(
    """Question: ${question}

<context>
${contexts}
</context>

Answer:"""
)


def build_prompt(
    question: str,
    contexts: list[str],
    lang_name: str = None,
) -> str:
    ctx = "\n\n".join(f"<source>\n{c}\n</source>" for c in contexts)

    lang_instruction = f"\nAnswer strictly in {lang_name}." if lang_name else ""
    return TEMPLATE.substitute(
        contexts=ctx,
        question=question.strip() + lang_instruction,
    )


if __name__ == "__main__":
    print(build_prompt("question", ["context 1", "context 2"], "system prompt"))
