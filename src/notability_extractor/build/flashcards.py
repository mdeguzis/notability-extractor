"""Flashcard output writers. Consume list[ArchivedCard], write .apkg / .json / .md."""

from __future__ import annotations

import json
from pathlib import Path

import genanki  # type: ignore[import-untyped]

from notability_extractor.model import ArchivedCard

# Stable IDs for the genanki model and deck. These are arbitrary integers
# but must remain consistent so Anki can identify them on re-import.
_MODEL_ID = 1607392319
_DECK_ID = 2059400110


def write_apkg(cards: list[ArchivedCard], path: Path, deck_name: str) -> None:
    """Build an Anki package from a list of archived cards and write to path."""
    model = genanki.Model(
        _MODEL_ID,
        "Notability MCQ",
        fields=[{"name": "Question"}, {"name": "Answer"}],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Question}}",
                "afmt": "{{FrontSide}}<hr id='answer'>{{Answer}}",
            }
        ],
    )
    deck = genanki.Deck(_DECK_ID, deck_name)

    for c in cards:
        opts = c.card.options
        # build the front side: question on top, then each option on its own line
        question_html = "<br>".join(
            [c.card.question] + [f"{k}. {opts[k]}" for k in sorted(opts.keys())]
        )
        correct_text = opts.get(c.card.correct_answer, "")
        answer_html = f"<b>{c.card.correct_answer}.</b> {correct_text}"
        note = genanki.Note(
            model=model,
            fields=[question_html, answer_html],
            tags=list(c.card.tags),
        )
        deck.add_note(note)

    path.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(deck).write_to_file(str(path))


def write_json(cards: list[ArchivedCard], path: Path) -> None:
    """Write cards as a JSON file with a top-level 'cards' array."""
    payload = {
        "cards": [
            {
                "id": c.id,
                "question": c.card.question,
                "options": c.card.options,
                "correct_answer": c.card.correct_answer,
                "tags": c.card.tags,
            }
            for c in cards
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def write_md(cards: list[ArchivedCard], path: Path) -> None:
    """Write cards as a Markdown file, one H2 per card with options listed below."""
    lines: list[str] = ["# Flashcards", ""]

    for c in cards:
        lines.append(f"## {c.card.question}")
        lines.append("")
        for letter in sorted(c.card.options.keys()):
            text = c.card.options[letter]
            # bold the letter marker for the correct answer so it stands out
            if letter == c.card.correct_answer:
                lines.append(f"- **{letter}**. {text}")
            else:
                lines.append(f"- {letter}. {text}")
        if c.card.tags:
            lines.append("")
            lines.append("Tags: " + ", ".join(c.card.tags))
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
