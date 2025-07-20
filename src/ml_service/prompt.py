from string import Template

TEMPLATE = Template(
    """Question: ${question}

<context>
${contexts}
</context>
"""
)


def build_prompt(
    question: str,
    contexts: list[dict],
    lang_name: str | None = None,
) -> str:
    fragments = []
    for ctx in contexts:
        fragments.append(f'<source resource="{ctx["resource"]}">\n{ctx["content"]}\n</source>')
    ctx_block = "\n\n".join(fragments)

    lang_instruction = f"\nAnswer strictly in {lang_name}." if lang_name else ""
    return TEMPLATE.substitute(
        question=question.strip() + lang_instruction,
        contexts=ctx_block,
    )
