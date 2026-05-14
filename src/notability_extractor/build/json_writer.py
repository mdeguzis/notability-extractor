"""Write a Deck as pretty-printed JSON."""

import json
from pathlib import Path
from typing import Any

from notability_extractor.model import Deck


def write_json_deck(deck: Deck, out_path: Path) -> None:
    obj: dict[str, Any] = {
        "deck_name": deck.name,
        "generated_at": deck.generated_at.isoformat(),
        "cards": [
            {
                "index": c.index,
                "source_file": c.source_file,
                "question": c.question,
                "options": c.options,
                "correct_answer": c.correct_answer,
                "correct_text": c.options.get(c.correct_answer, ""),
            }
            for c in deck.cards
        ],
        "summaries": [
            {"title": s.title, "source_file": s.source_file, "body": s.body}
            for s in deck.summaries
        ],
        "notes": [
            {"name": n.name, "source_file": n.source_file, "body": n.body} for n in deck.notes
        ],
    }
    out_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
