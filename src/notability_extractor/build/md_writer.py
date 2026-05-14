"""Render a Deck as human-readable Markdown for review."""

from pathlib import Path

from notability_extractor.model import Deck


def write_md_deck(deck: Deck, out_path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# {deck.name}")
    lines.append("")
    lines.append(f"Generated: {deck.generated_at.isoformat()}")
    lines.append("")

    lines.append(f"## Cards ({len(deck.cards)})")
    lines.append("")
    for i, c in enumerate(deck.cards, 1):
        lines.append(f"### {i}. {c.question}")
        lines.append("")
        for letter in ("A", "B", "C", "D"):
            text = c.options.get(letter, "")
            lines.append(f"- **{letter})** {text}")
        lines.append("")
        correct_text = c.options.get(c.correct_answer, "")
        lines.append(f"**Answer:** {c.correct_answer} - {correct_text}")
        lines.append("")
        lines.append(f"_Source: {c.source_file}_")
        lines.append("")

    if deck.summaries:
        lines.append(f"## Summaries ({len(deck.summaries)})")
        lines.append("")
        for s in deck.summaries:
            lines.append(f"### {s.title}")
            lines.append("")
            lines.append(f"_Source: {s.source_file}_")
            lines.append("")
            lines.append(s.body)
            lines.append("")

    if deck.notes:
        lines.append(f"## Note Transcripts ({len(deck.notes)})")
        lines.append("")
        for n in deck.notes:
            lines.append(f"### {n.name}")
            lines.append("")
            lines.append("```")
            lines.append(n.body)
            lines.append("```")
            lines.append("")

    out_path.write_text("\n".join(lines))
