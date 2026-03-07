"""All game enums for Oath simulator."""

from enum import IntEnum


class Suit(IntEnum):
    DISCORD = 0
    ARCANE = 1
    ORDER = 2
    HEARTH = 3
    BEAST = 4
    NOMAD = 5


class Region(IntEnum):
    CRADLE = 0
    PROVINCES = 1
    HINTERLAND = 2


class Role(IntEnum):
    CHANCELLOR = 0
    EXILE = 1
    CITIZEN = 2


class OathGoal(IntEnum):
    SUPREMACY = 0
    PEOPLE = 1
    DEVOTION = 2
    SANCTUARY = 3


class SuccessorGoal(IntEnum):
    MOST_SITES = 0
    MOST_RELICS_BANNERS = 1
    DARKEST_SECRET = 2
    PEOPLES_FAVOR = 3


class WinType(IntEnum):
    OATHKEEPER_DEFAULT = 0  # Chancellor kept oath through game end
    USURPER = 1             # Held Usurper title through a full round
    VISION = 2              # Exile met vision condition
    SUCCESSOR = 3           # Citizen beat Chancellor on successor goal


class TitleSide(IntEnum):
    OATHKEEPER = 0
    USURPER = 1


class CardRestriction(IntEnum):
    NONE = 0
    SITE_ONLY = 1
    ADVISER_ONLY = 2


class EffectTrigger(IntEnum):
    ACTION = 0
    MODIFIER = 1
    WHEN_PLAYED = 2
    BATTLE_PLAN = 3
    WAKE = 4
    PERSISTENT = 5
    REST = 6


class ModifierType(IntEnum):
    TRAVEL = 0
    SEARCH = 1
    MUSTER = 2
    TRADE = 3
    CAMPAIGN = 4
    RECOVER = 5


class Phase(IntEnum):
    WAKE = 0
    ACT = 1
    REST = 2


class ActionType(IntEnum):
    TRAVEL = 0
    SEARCH = 1
    MUSTER = 2
    TRADE_FAVOR = 3
    TRADE_SECRETS = 4
    RECOVER = 5
    RECOVER_PEOPLES_FAVOR = 6
    RECOVER_DARKEST_SECRET = 7
    CAMPAIGN_DECLARE = 8
    MINOR_FLIP_ADVISER = 9
    MINOR_USE_ACTION = 10
    MINOR_WARBANDS = 11
    MINOR_PEEK_RELIC = 12
    END_ACT_PHASE = 13
    OFFER_CITIZENSHIP = 14
    ACCEPT_CITIZENSHIP = 15
    DECLINE_CITIZENSHIP = 16
    SELF_EXILE = 17
    RELIQUARY_CHOOSE = 18
    CAMPAIGN_BATTLE_PLAN = 19
    CAMPAIGN_NO_BATTLE = 20
    CAMPAIGN_SACRIFICE = 21
    SEARCH_PLAY = 22
    SEARCH_DISCARD = 23
    CAMPAIGN_ADD_TARGET = 24
    CAMPAIGN_DONE_TARGETS = 25
    CAMPAIGN_TARGET_SITE = 26
    CAMPAIGN_TARGET_RELIC = 27
    CAMPAIGN_TARGET_PAWN = 28
    COMM_SIGNAL = 29
    COMM_TARGET = 30


class CompoundStateType(IntEnum):
    SEARCH_CHOOSE = 0
    CAMPAIGN_TARGETS = 1
    CAMPAIGN_BATTLE = 2
    CAMPAIGN_SACRIFICE = 3
    CITIZENSHIP_RESPONSE = 4
    RELIQUARY_CHOOSE = 5


# Game constants
MAX_PLAYERS = 6
MAX_SITES = 8
MAX_CARDS_PER_SITE = 3
MAX_ADVISERS = 3
MAX_RELICS_HELD = 6
MAX_RELICS_PER_SITE = 3
MAX_RELIQUARY = 4
MAX_WARBANDS_CHANCELLOR = 24
MAX_WARBANDS_EXILE = 14
MAX_SUPPLY = 9
MAX_ROUNDS = 8
MAX_VISIONS_DRAWN = 5
NUM_SUITS = 6
NUM_CARD_IDS = 230
NUM_REGIONS = 3
NUM_OATH_GOALS = 4
NUM_SUCCESSOR_GOALS = 4
MAX_FAVOR_TOTAL = 36
MAX_SECRETS_TOTAL = 20
NUM_ACTIONS = 119

# Clockwise suit order matching the favor bank layout on the map
# (See rulebook section 8.4: the suit order for adding cards)
SUIT_CLOCKWISE_ORDER = [
    Suit.ARCANE, Suit.BEAST, Suit.DISCORD,
    Suit.HEARTH, Suit.NOMAD, Suit.ORDER,
]

# Maps OathGoal to the corresponding SuccessorGoal
OATH_TO_SUCCESSOR: dict[int, int] = {
    OathGoal.SUPREMACY: SuccessorGoal.MOST_SITES,
    OathGoal.PEOPLE: SuccessorGoal.PEOPLES_FAVOR,
    OathGoal.DEVOTION: SuccessorGoal.DARKEST_SECRET,
    OathGoal.SANCTUARY: SuccessorGoal.MOST_RELICS_BANNERS,
}

# Maps Vision card IDs to the OathGoal they correspond to
VISION_TO_OATH_GOAL: dict[int, int] = {
    221: OathGoal.SUPREMACY,   # Vision of Conquest
    222: OathGoal.DEVOTION,     # Vision of Faith
    223: OathGoal.PEOPLE,       # Vision of Rebellion
    224: OathGoal.SANCTUARY,    # Vision of Sanctuary
    # 225 (Conspiracy) has no corresponding oath goal
}
