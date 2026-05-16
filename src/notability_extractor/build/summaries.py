"""Summaries output writers. Consume list[Summary], write .json / .md."""

from __future__ import annotations

import json
from pathlib import Path

from notability_extractor.model import Summary


def write_json(items: list[Summary], path: Path) -> None:
    """Write summaries as a JSON file with a top-level 'summaries' array."""
    payload = {
        "summaries": [
            {"title": s.title, "body": s.body, "source_file": s.source_file} for s in items
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def write_md(items: list[Summary], path: Path) -> None:
    """Write summaries as a Markdown file, concatenating each body in order.

    If a summary body already starts with a '#' heading, use it as-is.
    Otherwise prefix it with an H2 from the title so the output stays navigable.
    """
    lines: list[str] = ["# Summaries", ""]

    for s in items:
        if s.body.startswith("# "):
            lines.append(s.body)
        else:
            lines.append(f"## {s.title}\n\n{s.body}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
