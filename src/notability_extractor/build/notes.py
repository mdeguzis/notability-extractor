"""Notes output writers. Consume list[NoteText], write .json / .md."""

from __future__ import annotations

import json
from pathlib import Path

from notability_extractor.model import NoteText


def write_json(items: list[NoteText], path: Path) -> None:
    """Write notes as a JSON file with a top-level 'notes' array."""
    payload = {
        "notes": [{"name": n.name, "body": n.body, "source_file": n.source_file} for n in items]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def write_md(items: list[NoteText], path: Path) -> None:
    """Write notes as a Markdown file, one H2 per note followed by its body."""
    lines: list[str] = ["# Notes", ""]

    for n in items:
        lines.append(f"## {n.name}")
        lines.append("")
        lines.append(n.body)
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
