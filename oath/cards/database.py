"""Card database for Oath simulator.

Contains all 230 cards. First-game cards are fully defined;
others are stubbed with basic info.
"""

from __future__ import annotations

from oath.enums import Suit, CardRestriction, NUM_SUITS
from oath.cards.card import CardData

# Master card database indexed by card_id
CARD_DB: dict[int, CardData] = {}


def _register(card: CardData) -> CardData:
    CARD_DB[card.card_id] = card
    return card


def get_card(card_id: int) -> CardData:
    """Look up a card by ID. Returns padding card for id=0."""
    return CARD_DB.get(card_id, CARD_DB[0])


# ── ID 0: Padding / empty ──────────────────────────────────────────
_register(CardData(card_id=0, name="Empty"))

# ── Sites (IDs 201–208) ────────────────────────────────────────────
_register(CardData(card_id=201, name="Plains", is_site=True, capacity=3, defense=1, starting_favor=1))
_register(CardData(card_id=202, name="Mountain", is_site=True, capacity=2, defense=3, starting_secrets=1))
_register(CardData(card_id=203, name="Rocky Coast", is_site=True, capacity=2, defense=2, starting_favor=1))
_register(CardData(card_id=204, name="Lush Coast", is_site=True, capacity=3, defense=1, starting_favor=2))
_register(CardData(card_id=205, name="Narrow Pass", is_site=True, capacity=1, defense=4))
_register(CardData(card_id=206, name="Mine", is_site=True, capacity=2, defense=2, starting_secrets=1))
_register(CardData(card_id=207, name="Wastes", is_site=True, capacity=2, defense=1, starting_favor=1))
_register(CardData(card_id=208, name="Salt Flats", is_site=True, capacity=1, defense=2, starting_secrets=1))

# ── Visions (IDs 221–225) ──────────────────────────────────────────
_register(CardData(card_id=221, name="Vision of Conquest", is_vision=True))
_register(CardData(card_id=222, name="Vision of Faith", is_vision=True))
_register(CardData(card_id=223, name="Vision of Rebellion", is_vision=True))
_register(CardData(card_id=224, name="Vision of Sanctuary", is_vision=True))
_register(CardData(card_id=225, name="Vision of Conspiracy", is_vision=True))

# ── Relics (IDs 211–220) ───────────────────────────────────────────
_register(CardData(card_id=211, name="Grand Scepter", is_relic=True))
_register(CardData(card_id=212, name="Ivory Eye", is_relic=True))
_register(CardData(card_id=213, name="Cup of Plenty", is_relic=True))
_register(CardData(card_id=214, name="Book of Records", is_relic=True))
_register(CardData(card_id=215, name="Skeleton Key", is_relic=True))
_register(CardData(card_id=216, name="Spirit Snare", is_relic=True))
_register(CardData(card_id=217, name="Relic 7", is_relic=True))
_register(CardData(card_id=218, name="Relic 8", is_relic=True))
_register(CardData(card_id=219, name="Relic 9", is_relic=True))
_register(CardData(card_id=220, name="Relic 10", is_relic=True))

# ── First-game Denizens (IDs 1–30) ─────────────────────────────────
_register(CardData(card_id=1, name="Longbows", suit=Suit.ORDER, restriction=CardRestriction.NONE))
_register(CardData(card_id=2, name="Taming Charm", suit=Suit.BEAST, restriction=CardRestriction.NONE))
_register(CardData(card_id=3, name="Elders", suit=Suit.HEARTH, restriction=CardRestriction.ADVISER_ONLY))
_register(CardData(card_id=4, name="Forest Paths", suit=Suit.NOMAD, restriction=CardRestriction.ADVISER_ONLY))
_register(CardData(card_id=5, name="Animal Playmates", suit=Suit.BEAST, restriction=CardRestriction.NONE))
_register(CardData(card_id=6, name="Naysayers", suit=Suit.DISCORD, restriction=CardRestriction.NONE))
_register(CardData(card_id=7, name="A Small Favor", suit=Suit.HEARTH, restriction=CardRestriction.NONE))
_register(CardData(card_id=8, name="Garrison", suit=Suit.ORDER, restriction=CardRestriction.SITE_ONLY))
_register(CardData(card_id=9, name="Errand Boy", suit=Suit.NOMAD, restriction=CardRestriction.NONE))
_register(CardData(card_id=10, name="The Old Oak", suit=Suit.BEAST, restriction=CardRestriction.SITE_ONLY))
_register(CardData(card_id=11, name="Alchemist", suit=Suit.ARCANE, restriction=CardRestriction.ADVISER_ONLY))
_register(CardData(card_id=12, name="Scryer", suit=Suit.ARCANE, restriction=CardRestriction.ADVISER_ONLY))
_register(CardData(card_id=13, name="Bear Traps", suit=Suit.BEAST, restriction=CardRestriction.SITE_ONLY))
_register(CardData(card_id=14, name="Wayside Inn", suit=Suit.HEARTH, restriction=CardRestriction.SITE_ONLY))
_register(CardData(card_id=15, name="Keep", suit=Suit.ORDER, restriction=CardRestriction.SITE_ONLY))
_register(CardData(card_id=16, name="Tents", suit=Suit.NOMAD, restriction=CardRestriction.SITE_ONLY))
_register(CardData(card_id=17, name="Wrestlers", suit=Suit.DISCORD, restriction=CardRestriction.NONE))
_register(CardData(card_id=18, name="Pressgangs", suit=Suit.ORDER, restriction=CardRestriction.NONE))
_register(CardData(card_id=19, name="Sticky Fire", suit=Suit.ARCANE, restriction=CardRestriction.NONE))

# ── Edifices (IDs 226–230) ─────────────────────────────────────────
_register(CardData(card_id=226, name="Great Hall", is_edifice=True, suit=Suit.ORDER))
_register(CardData(card_id=227, name="Ancient City", is_edifice=True, suit=Suit.ARCANE))
_register(CardData(card_id=228, name="Fallen Monastery", is_edifice=True, suit=Suit.DISCORD))
_register(CardData(card_id=229, name="Ruined Tower", is_edifice=True, suit=Suit.BEAST))
_register(CardData(card_id=230, name="Broken Bridge", is_edifice=True, suit=Suit.NOMAD))

# ── Stub remaining denizens (IDs 20–198) ───────────────────────────
for _id in range(20, 199):
    if _id not in CARD_DB:
        _register(CardData(
            card_id=_id,
            name=f"Denizen_{_id}",
            suit=Suit(_id % NUM_SUITS),
        ))

# ── Stub remaining relics (if any gaps) ────────────────────────────
for _id in range(211, 221):
    if _id not in CARD_DB:
        _register(CardData(card_id=_id, name=f"Relic_{_id}", is_relic=True))


def get_first_game_denizen_ids() -> list[int]:
    """Return card IDs for the first-game denizen setup."""
    return list(range(1, 20))


def get_first_game_site_ids() -> list[int]:
    """Return card IDs for the first-game site setup."""
    return list(range(201, 209))


def get_first_game_relic_ids() -> list[int]:
    """Return card IDs for the first-game relic setup."""
    return list(range(211, 217))


def get_vision_ids() -> list[int]:
    """Return all Vision card IDs."""
    return list(range(221, 226))


def get_all_denizen_ids() -> list[int]:
    """Return all denizen card IDs."""
    return list(range(1, 199))
