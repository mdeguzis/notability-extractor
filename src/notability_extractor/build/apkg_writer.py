"""Translate a Deck into the dict shape anki.write_apkg expects."""

from pathlib import Path

from notability_extractor.anki import write_apkg
from notability_extractor.model import Card, Deck


def write_apkg_deck(deck: Deck, out_path: Path) -> None:
    cards_dicts = [_card_to_dict(c) for c in deck.cards]
    write_apkg(cards_dicts, deck.name, out_path)


def _card_to_dict(card: Card) -> dict[str, str]:
    opts = card.options
    front = (
        f"{card.question}\n\n"
        f"A) {opts.get('A', '')}\n"
        f"B) {opts.get('B', '')}\n"
        f"C) {opts.get('C', '')}\n"
        f"D) {opts.get('D', '')}"
    )
    correct_text = opts.get(card.correct_answer, "")
    back = f"{card.correct_answer} - {correct_text}"
    return {"front": front, "back": back}
