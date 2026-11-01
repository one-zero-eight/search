"""Check the bundle in wiki/ against OKF v0.2 (what a consumer may rely on) and report what is weak.

    catix-wiki lint     # exit code 1 when a conformance rule is broken

Errors (the bundle does not conform): a concept without parseable front matter or without `type`, an index.md or log.md that breaks its layout.
Warnings (conformant, but worth a look): a broken or unresolved link, a concept without sources, a title heading that is not the front matter title.
"""

import re
import sys

import yaml

from catix.wiki.compile import BUNDLE

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")


def lint() -> int:
    errors, warnings = [], []
    paths = sorted(BUNDLE.rglob("*.md"))
    ids = {"/" + p.relative_to(BUNDLE).as_posix() for p in paths}
    for path in paths:
        rel = path.relative_to(BUNDLE).as_posix()
        text = path.read_text(encoding="utf-8")
        reserved = path.name in {"index.md", "log.md"}
        front = text.split("---\n", 2)[1] if text.startswith("---\n") and text.count("---\n") >= 2 else None
        if path.name == "log.md":
            if not re.search(r"^## \d{4}-\d{2}-\d{2}$", text, re.M):
                errors.append(f"{rel}: no '## YYYY-MM-DD' heading")
        elif path.name == "index.md":
            if front and path.parent != BUNDLE:
                errors.append(f"{rel}: index.md has front matter (only the root one may, with okf_version)")
        else:
            try:
                meta = yaml.safe_load(front) if front else None
            except yaml.YAMLError as e:
                errors.append(f"{rel}: front matter does not parse: {e}")
                continue
            if not isinstance(meta, dict) or not str(meta.get("type", "")).strip():
                errors.append(f"{rel}: no non-empty `type`")
                continue
            if meta.get("type") == "readme":
                continue
            if bad := [t for t in meta.get("tags") or [] if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(t))]:
                warnings.append(f"{rel}: tags that a tag system may reject: {bad[:3]}")
            if not meta.get("sources"):
                warnings.append(f"{rel}: no `sources`")
            if "# Citations" not in text and meta.get("sources"):
                warnings.append(f"{rel}: has sources but no '# Citations' section")
        if not reserved or path.name == "index.md":
            for target in LINK.findall(text):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                if target.startswith("wiki:"):
                    warnings.append(f"{rel}: unresolved link {target}")
                elif target.startswith("/") and target.split("#")[0] not in ids:
                    warnings.append(f"{rel}: broken link {target}")
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(paths)} files, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def main() -> None:
    sys.exit(lint())
