"""Read an input directory into a Deck object."""

import json
from datetime import UTC, datetime
from pathlib import Path

from notability_extractor.model import Card, Deck, NoteText, Summary
from notability_extractor.utils import get_logger

log = get_logger(__name__)


def read_input_dir(
    input_dir: Path,
    deck_name: str = "Notability Flashcards",
) -> Deck:
    """Walk input_dir and produce a Deck."""
    cards = _read_quizzes(input_dir / "learn" / "quizzes")
    summaries = _read_summaries(input_dir / "learn" / "summaries")
    notes = _read_notes(input_dir)
    log.debug(
        "Loaded input dir %s: %d cards, %d summaries, %d notes",
        input_dir,
        len(cards),
        len(summaries),
        len(notes),
    )
    return Deck(
        name=deck_name,
        generated_at=datetime.now(UTC),
        cards=cards,
        summaries=summaries,
        notes=notes,
    )


def _read_quizzes(quizzes_dir: Path) -> list[Card]:
    if not quizzes_dir.is_dir():
        return []
    cards: list[Card] = []
    for json_file in sorted(quizzes_dir.glob("*.json")):
        with json_file.open() as f:
            outer = json.load(f)
        # quiz JSON is double-encoded: data.getQuizJobContent is itself a JSON string
        inner_str = outer["data"]["getQuizJobContent"]
        inner = json.loads(inner_str)
        for i, q in enumerate(inner["questions"], 1):
            cards.append(
                Card(
                    question=q["question"],
                    options=q["answers"],
                    correct_answer=q["correct_answer"],
                    source_file=json_file.name,
                    index=i,
                )
            )
    return cards


def _read_summaries(summaries_dir: Path) -> list[Summary]:
    if not summaries_dir.is_dir():
        return []
    out: list[Summary] = []
    for md_file in sorted(summaries_dir.glob("*.md")):
        body = md_file.read_text()
        title = _extract_first_h1(body) or md_file.stem
        out.append(Summary(title=title, body=body, source_file=md_file.name))
    return out


def _read_notes(export_dir: Path) -> list[NoteText]:
    out: list[NoteText] = []
    # top-level *.txt only - learn/ has its own files we don't want here
    for txt_file in sorted(export_dir.glob("*.txt")):
        body = txt_file.read_text()
        out.append(NoteText(name=txt_file.stem, body=body, source_file=txt_file.name))
    return out


def _extract_first_h1(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None
