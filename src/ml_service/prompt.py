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
    lang_name: str = None,
) -> str:
    ctx = "\n\n".join(f"- {c}" for c in contexts)
    lang_instruction = f"\n\nAnswer strictly in {lang_name}." if lang_name else ""
    return TEMPLATE.substitute(
        system_prompt=system_prompt.strip() + lang_instruction,
        contexts=ctx,
        question=question.strip(),
    )


if __name__ == "__main__":
    print(build_prompt("question", ["context 1", "context 2"], "system prompt"))
