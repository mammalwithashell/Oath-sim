"""Card dataclasses for Oath simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from oath.enums import Suit, CardRestriction


@dataclass(frozen=True)
class CardData:
    """Static card data from the database (immutable)."""
    card_id: int
    name: str
    suit: Optional[Suit] = None
    is_vision: bool = False
    is_relic: bool = False
    is_edifice: bool = False
    is_site: bool = False
    restriction: CardRestriction = CardRestriction.NONE
    capacity: int = 0  # Only for sites
    starting_favor: int = 0  # Favor placed on site when revealed
    starting_secrets: int = 0  # Secrets placed on site when revealed
    defense: int = 0  # Site defense value
    oath_id: Optional[str] = None  # Official ID e.g. "OATH-042"


@dataclass
class CardInstance:
    """Runtime state of a card in play."""
    card_id: int
    faceup: bool = True
    is_ruined: bool = False  # Only for edifices
    favor_on: int = 0
    secrets_on: int = 0
