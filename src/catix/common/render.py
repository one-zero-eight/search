"""Turns the model's Markdown into HTML for messengers and splits long answers."""

import html
import re


def to_html(markdown: str) -> str:
    """Convert the subset of Markdown the model writes into the HTML subset Telegram and Max accept."""
    text = html.escape(markdown, quote=False)
    text = re.sub(r"```(?:\w+)?\n?(.*?)```", r"<pre>\1</pre>", text, flags=re.S)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.M)
    text = re.sub(r"^(\s*)[*-]\s+", r"\1• ", text, flags=re.M)
    return text


def chunks(text: str, size: int) -> list[str]:
    parts = []
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        cut = cut if cut > 0 else size
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return [*parts, text] if text else parts
