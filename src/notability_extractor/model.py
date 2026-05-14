"""
Data model for the notability-extractor pipeline.

A Deck is the in-memory shape both Phase 1 (extract) outputs implicitly
(via the export directory layout) and Phase 2 (build) consumes explicitly
(via the reader, then handed to each writer).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Card:
    """One MCQ from a Notability Learn quiz. One JSON entry = one Card."""

    question: str
    options: dict[str, str]
    correct_answer: str
    source_file: str
    index: int


@dataclass(frozen=True)
class Summary:
    """AI-generated summary, one per Notability Learn session."""

    title: str
    body: str
    source_file: str


@dataclass(frozen=True)
class NoteText:
    """Handwriting OCR + PDF text for one note bundle, combined."""

    name: str
    body: str
    source_file: str


@dataclass
class Deck:
    """All extracted content for one extraction run."""

    name: str
    generated_at: datetime
    cards: list[Card]
    summaries: list[Summary]
    notes: list[NoteText]
