"""
Data model for the notability-extractor pipeline.

A Deck is the in-memory shape both Phase 1 (extract) outputs implicitly
(via the export directory layout) and Phase 2 (build) consumes explicitly
(via the reader, then handed to each writer).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Card:
    """One MCQ from a Notability Learn quiz. One JSON entry = one Card."""

    question: str
    options: dict[str, str]
    correct_answer: str
    source_file: str
    index: int
    tags: list[str] = field(default_factory=list)

    @property
    def stable_id(self) -> str:
        # md5 of question + the text of the correct option. Lets the archive
        # spot duplicates across re-extractions even if option order shuffles.
        material = self.question + "|" + self.options.get(self.correct_answer, "")
        return hashlib.md5(material.encode("utf-8"), usedforsecurity=False).hexdigest()


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


@dataclass(frozen=True)
class ArchivedCard:
    """A Card plus the metadata the archive tracks for it.

    `id` is set to `Card.stable_id` at first archive write and frozen.
    If the card's question is later edited, `stable_id` changes but `id`
    does NOT, so edit history survives typo fixes.
    """

    card: Card
    id: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Deck:
    """All extracted content for one extraction run."""

    name: str
    generated_at: datetime
    cards: list[Card]
    summaries: list[Summary]
    notes: list[NoteText]
