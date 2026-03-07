"""Site state dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from oath.enums import Region


@dataclass
class SiteState:
    """Mutable state for a single site."""
    site_id: int
    region: Region
    is_faceup: bool = False
    capacity: int = 3
    cards: list[Optional[int]] = field(default_factory=lambda: [None, None, None])
    card_favor: list[int] = field(default_factory=lambda: [0, 0, 0])
    card_secrets: list[int] = field(default_factory=lambda: [0, 0, 0])
    relics: list[int] = field(default_factory=list)
    ruling_player: Optional[int] = None
    warbands: int = 0
    site_favor: int = 0
    site_secrets: int = 0

    @property
    def num_cards(self) -> int:
        return sum(1 for c in self.cards[:self.capacity] if c is not None)

    def has_empty_card_slot(self) -> bool:
        return any(c is None for c in self.cards[:self.capacity])

    def first_empty_card_slot(self) -> Optional[int]:
        for i in range(self.capacity):
            if self.cards[i] is None:
                return i
        return None

    @property
    def is_ruled(self) -> bool:
        return self.ruling_player is not None
