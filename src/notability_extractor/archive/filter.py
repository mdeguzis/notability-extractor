"""Pure filter helpers over a list[ArchivedCard]. No I/O."""

from __future__ import annotations

from typing import Literal

from notability_extractor.model import ArchivedCard


def by_tags(
    cards: list[ArchivedCard],
    tags: list[str],
    mode: Literal["any", "all"] = "any",
) -> list[ArchivedCard]:
    """Filter to cards matching given tags. mode='any' = union, 'all' = intersection."""
    if not tags:
        return list(cards)
    wanted = set(tags)
    if mode == "all":
        return [c for c in cards if wanted.issubset(c.card.tags)]
    return [c for c in cards if wanted.intersection(c.card.tags)]


def by_text(cards: list[ArchivedCard], query: str) -> list[ArchivedCard]:
    """Case-insensitive substring match against question + every option's text."""
    if not query:
        return list(cards)
    needle = query.lower()
    out: list[ArchivedCard] = []
    for c in cards:
        if needle in c.card.question.lower():
            out.append(c)
            continue
        if any(needle in v.lower() for v in c.card.options.values()):
            out.append(c)
    return out


def all_tags(cards: list[ArchivedCard]) -> list[str]:
    """Sorted unique tags across all cards. Feeds tag-input autocomplete."""
    seen: set[str] = set()
    for c in cards:
        seen.update(c.card.tags)
    return sorted(seen, key=str.lower)
