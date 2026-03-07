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
_register(CardData(card_id=211, name="Grand Scepter", is_relic=True, oath_id="OATH-231"))
_register(CardData(card_id=212, name="Ivory Eye", is_relic=True, oath_id="OATH-226"))
_register(CardData(card_id=213, name="Cup of Plenty", is_relic=True, oath_id="OATH-217"))
_register(CardData(card_id=214, name="Book of Records", is_relic=True, oath_id="OATH-229"))
_register(CardData(card_id=215, name="Skeleton Key", is_relic=True, oath_id="OATH-223"))
_register(CardData(card_id=216, name="Horned Mask", is_relic=True, oath_id="OATH-216"))
_register(CardData(card_id=217, name="Whistle", is_relic=True, oath_id="OATH-218"))
_register(CardData(card_id=218, name="Dowsing Sticks", is_relic=True, oath_id="OATH-219"))
_register(CardData(card_id=219, name="Cursed Cauldron", is_relic=True, oath_id="OATH-212"))
_register(CardData(card_id=220, name="Brass Horse", is_relic=True, oath_id="OATH-213"))

# ── First-game Denizens (IDs 1–19) ────────────────────────────────
_register(CardData(card_id=1, name="Longbows", suit=Suit.ORDER, restriction=CardRestriction.NONE, oath_id="OATH-004"))
_register(CardData(card_id=2, name="Taming Charm", suit=Suit.BEAST, restriction=CardRestriction.NONE, oath_id="OATH-037"))
_register(CardData(card_id=3, name="Elders", suit=Suit.HEARTH, restriction=CardRestriction.ADVISER_ONLY, oath_id="OATH-026"))
_register(CardData(card_id=4, name="Forest Paths", suit=Suit.NOMAD, restriction=CardRestriction.ADVISER_ONLY, oath_id="OATH-043"))
_register(CardData(card_id=5, name="Animal Playmates", suit=Suit.BEAST, restriction=CardRestriction.NONE, oath_id="OATH-040"))
_register(CardData(card_id=6, name="Naysayers", suit=Suit.DISCORD, restriction=CardRestriction.NONE, oath_id="OATH-021"))
_register(CardData(card_id=7, name="A Small Favor", suit=Suit.HEARTH, restriction=CardRestriction.NONE, oath_id="OATH-015"))
_register(CardData(card_id=8, name="Garrison", suit=Suit.ORDER, restriction=CardRestriction.SITE_ONLY, oath_id="OATH-007"))
_register(CardData(card_id=9, name="Errand Boy", suit=Suit.NOMAD, restriction=CardRestriction.NONE, oath_id="OATH-011"))
_register(CardData(card_id=10, name="The Old Oak", suit=Suit.BEAST, restriction=CardRestriction.SITE_ONLY, oath_id="OATH-042"))
_register(CardData(card_id=11, name="Alchemist", suit=Suit.ARCANE, restriction=CardRestriction.ADVISER_ONLY, oath_id="OATH-009"))
_register(CardData(card_id=12, name="Scryer", suit=Suit.ARCANE, restriction=CardRestriction.ADVISER_ONLY, oath_id="OATH-019"))
_register(CardData(card_id=13, name="Bear Traps", suit=Suit.BEAST, restriction=CardRestriction.SITE_ONLY, oath_id="OATH-003"))
_register(CardData(card_id=14, name="Wayside Inn", suit=Suit.HEARTH, restriction=CardRestriction.SITE_ONLY, oath_id="OATH-047"))
_register(CardData(card_id=15, name="Keep", suit=Suit.ORDER, restriction=CardRestriction.SITE_ONLY, oath_id="OATH-005"))
_register(CardData(card_id=16, name="Tents", suit=Suit.NOMAD, restriction=CardRestriction.SITE_ONLY, oath_id="OATH-029"))
_register(CardData(card_id=17, name="Wrestlers", suit=Suit.DISCORD, restriction=CardRestriction.NONE, oath_id="OATH-001"))
_register(CardData(card_id=18, name="Pressgangs", suit=Suit.ORDER, restriction=CardRestriction.NONE, oath_id="OATH-006"))
_register(CardData(card_id=19, name="Sticky Fire", suit=Suit.ARCANE, restriction=CardRestriction.NONE, oath_id="OATH-211"))

# ── Edifices (IDs 226–230) ─────────────────────────────────────────
_register(CardData(card_id=226, name="Sprawling Rampart", is_edifice=True, suit=Suit.ORDER, oath_id="OATH-199"))
_register(CardData(card_id=227, name="Fallen Spire", is_edifice=True, suit=Suit.ARCANE, oath_id="OATH-208"))
_register(CardData(card_id=228, name="Squalid District", is_edifice=True, suit=Suit.DISCORD, oath_id="OATH-206"))
_register(CardData(card_id=229, name="Ruined Temple", is_edifice=True, suit=Suit.BEAST, oath_id="OATH-204"))
_register(CardData(card_id=230, name="Ancient Forge", is_edifice=True, suit=Suit.NOMAD, oath_id="OATH-209"))

# ── Remaining Denizens (IDs 20–199) ──────────────────────────────
_register(CardData(card_id=20, name="Battle Honors", suit=Suit.ORDER, oath_id="OATH-002"))
_register(CardData(card_id=21, name="Scouts", suit=Suit.ORDER, oath_id="OATH-008"))
_register(CardData(card_id=22, name="Martial Culture", suit=Suit.ORDER, oath_id="OATH-010"))
_register(CardData(card_id=23, name="Mercenaries", suit=Suit.DISCORD, oath_id="OATH-012"))
_register(CardData(card_id=24, name="Tinker's Fair", suit=Suit.HEARTH, oath_id="OATH-013"))
_register(CardData(card_id=25, name="Rain Boots", suit=Suit.NOMAD, oath_id="OATH-014"))
_register(CardData(card_id=26, name="Second Wind", suit=Suit.DISCORD, oath_id="OATH-016"))
_register(CardData(card_id=27, name="Sleight of Hand", suit=Suit.DISCORD, oath_id="OATH-017"))
_register(CardData(card_id=28, name="Key to the City", suit=Suit.DISCORD, oath_id="OATH-018"))
_register(CardData(card_id=29, name="Disgraced Captain", suit=Suit.DISCORD, oath_id="OATH-020"))
_register(CardData(card_id=30, name="Book Burning", suit=Suit.DISCORD, oath_id="OATH-022"))
_register(CardData(card_id=31, name="Ancient Binding", suit=Suit.NOMAD, oath_id="OATH-023"))
_register(CardData(card_id=32, name="Horse Archers", suit=Suit.NOMAD, oath_id="OATH-024"))
_register(CardData(card_id=33, name="Warning Signals", suit=Suit.NOMAD, oath_id="OATH-025"))
_register(CardData(card_id=34, name="The Gathering", suit=Suit.NOMAD, oath_id="OATH-027"))
_register(CardData(card_id=35, name="Faithful Friend", suit=Suit.NOMAD, oath_id="OATH-028"))
_register(CardData(card_id=36, name="Great Herd", suit=Suit.NOMAD, oath_id="OATH-030"))
_register(CardData(card_id=37, name="Fire Talkers", suit=Suit.ARCANE, oath_id="OATH-031"))
_register(CardData(card_id=38, name="Magician's Code", suit=Suit.ARCANE, oath_id="OATH-032"))
_register(CardData(card_id=39, name="Spirit Snare", suit=Suit.ARCANE, oath_id="OATH-033"))
_register(CardData(card_id=40, name="Wizard School", suit=Suit.ARCANE, oath_id="OATH-034"))
_register(CardData(card_id=41, name="Dazzle", suit=Suit.ARCANE, oath_id="OATH-035"))
_register(CardData(card_id=42, name="Acting Troupe", suit=Suit.ARCANE, oath_id="OATH-036"))
_register(CardData(card_id=43, name="Inquisitor", suit=Suit.ARCANE, oath_id="OATH-038"))
_register(CardData(card_id=44, name="Wolves", suit=Suit.BEAST, oath_id="OATH-039"))
_register(CardData(card_id=45, name="True Names", suit=Suit.BEAST, oath_id="OATH-041"))
_register(CardData(card_id=46, name="Long-Lost Heir", suit=Suit.BEAST, oath_id="OATH-044"))
_register(CardData(card_id=47, name="Rangers", suit=Suit.BEAST, oath_id="OATH-045"))
_register(CardData(card_id=48, name="Roving Terror", suit=Suit.BEAST, oath_id="OATH-046"))
_register(CardData(card_id=49, name="Extra Provisions", suit=Suit.HEARTH, oath_id="OATH-048"))
_register(CardData(card_id=50, name="Memory of Home", suit=Suit.HEARTH, oath_id="OATH-049"))
_register(CardData(card_id=51, name="Welcoming Party", suit=Suit.HEARTH, oath_id="OATH-050"))
_register(CardData(card_id=52, name="Traveling Doctor", suit=Suit.HEARTH, oath_id="OATH-051"))
_register(CardData(card_id=53, name="Storyteller", suit=Suit.HEARTH, oath_id="OATH-052"))
_register(CardData(card_id=54, name="Armed Mob", suit=Suit.HEARTH, oath_id="OATH-053"))
_register(CardData(card_id=55, name="Tavern Songs", suit=Suit.HEARTH, oath_id="OATH-054"))
_register(CardData(card_id=56, name="Secret Signal", suit=Suit.ARCANE, oath_id="OATH-055"))
_register(CardData(card_id=57, name="Augury", suit=Suit.ARCANE, oath_id="OATH-056"))
_register(CardData(card_id=58, name="Rusting Ray", suit=Suit.ARCANE, oath_id="OATH-057"))
_register(CardData(card_id=59, name="Portal", suit=Suit.ARCANE, oath_id="OATH-058"))
_register(CardData(card_id=60, name="Billowing Fog", suit=Suit.ARCANE, oath_id="OATH-059"))
_register(CardData(card_id=61, name="Kindred Warriors", suit=Suit.ARCANE, oath_id="OATH-060"))
_register(CardData(card_id=62, name="Terror Spells", suit=Suit.ARCANE, oath_id="OATH-061"))
_register(CardData(card_id=63, name="Blood Pact", suit=Suit.ARCANE, oath_id="OATH-062"))
_register(CardData(card_id=64, name="Revelation", suit=Suit.ARCANE, oath_id="OATH-063"))
_register(CardData(card_id=65, name="Observatory", suit=Suit.ARCANE, oath_id="OATH-064"))
_register(CardData(card_id=66, name="Plague Engines", suit=Suit.ARCANE, oath_id="OATH-065"))
_register(CardData(card_id=67, name="Gleaming Armor", suit=Suit.ARCANE, oath_id="OATH-066"))
_register(CardData(card_id=68, name="Bewitch", suit=Suit.ARCANE, oath_id="OATH-067"))
_register(CardData(card_id=69, name="Jinx", suit=Suit.ARCANE, oath_id="OATH-068"))
_register(CardData(card_id=70, name="Tutor", suit=Suit.ARCANE, oath_id="OATH-069"))
_register(CardData(card_id=71, name="Dream Thief", suit=Suit.ARCANE, oath_id="OATH-070"))
_register(CardData(card_id=72, name="Cracking Ground", suit=Suit.ARCANE, oath_id="OATH-071"))
_register(CardData(card_id=73, name="Sealing Ward", suit=Suit.ARCANE, oath_id="OATH-072"))
_register(CardData(card_id=74, name="Initiation Rite", suit=Suit.ARCANE, oath_id="OATH-073"))
_register(CardData(card_id=75, name="Vow of Silence", suit=Suit.ARCANE, oath_id="OATH-074"))
_register(CardData(card_id=76, name="Forgotten Vault", suit=Suit.ARCANE, oath_id="OATH-075"))
_register(CardData(card_id=77, name="Map Library", suit=Suit.ARCANE, oath_id="OATH-076"))
_register(CardData(card_id=78, name="Witch's Bargain", suit=Suit.ARCANE, oath_id="OATH-077"))
_register(CardData(card_id=79, name="Master of Disguise", suit=Suit.ARCANE, oath_id="OATH-078"))
_register(CardData(card_id=80, name="Charlatan", suit=Suit.DISCORD, oath_id="OATH-079"))
_register(CardData(card_id=81, name="Assassin", suit=Suit.DISCORD, oath_id="OATH-080"))
_register(CardData(card_id=82, name="Downtrodden", suit=Suit.DISCORD, oath_id="OATH-081"))
_register(CardData(card_id=83, name="Blackmail", suit=Suit.DISCORD, oath_id="OATH-082"))
_register(CardData(card_id=84, name="Cracked Sage", suit=Suit.DISCORD, oath_id="OATH-083"))
_register(CardData(card_id=85, name="Dissent", suit=Suit.DISCORD, oath_id="OATH-084"))
_register(CardData(card_id=86, name="False Prophet", suit=Suit.DISCORD, oath_id="OATH-085"))
_register(CardData(card_id=87, name="Vow of Renewal", suit=Suit.DISCORD, oath_id="OATH-086"))
_register(CardData(card_id=88, name="Zealots", suit=Suit.DISCORD, oath_id="OATH-087"))
_register(CardData(card_id=89, name="Royal Ambitions", suit=Suit.DISCORD, oath_id="OATH-088"))
_register(CardData(card_id=90, name="Salt the Earth", suit=Suit.DISCORD, oath_id="OATH-089"))
_register(CardData(card_id=91, name="Beast Tamer", suit=Suit.DISCORD, oath_id="OATH-090"))
_register(CardData(card_id=92, name="Riots", suit=Suit.DISCORD, oath_id="OATH-091"))
_register(CardData(card_id=93, name="Silver Tongue", suit=Suit.DISCORD, oath_id="OATH-092"))
_register(CardData(card_id=94, name="Gambling Hall", suit=Suit.DISCORD, oath_id="OATH-093"))
_register(CardData(card_id=95, name="Boiling Lake", suit=Suit.DISCORD, oath_id="OATH-094"))
_register(CardData(card_id=96, name="Relic Thief", suit=Suit.DISCORD, oath_id="OATH-095"))
_register(CardData(card_id=97, name="Enchantress", suit=Suit.DISCORD, oath_id="OATH-096"))
_register(CardData(card_id=98, name="Insomnia", suit=Suit.DISCORD, oath_id="OATH-097"))
_register(CardData(card_id=99, name="Sneak Attack", suit=Suit.DISCORD, oath_id="OATH-098"))
_register(CardData(card_id=100, name="Gossip", suit=Suit.DISCORD, oath_id="OATH-099"))
_register(CardData(card_id=101, name="Bandit Chief", suit=Suit.DISCORD, oath_id="OATH-100"))
_register(CardData(card_id=102, name="Chaos Cult", suit=Suit.DISCORD, oath_id="OATH-101"))
_register(CardData(card_id=103, name="Slander", suit=Suit.DISCORD, oath_id="OATH-102"))
_register(CardData(card_id=104, name="Code of Honor", suit=Suit.ORDER, oath_id="OATH-103"))
_register(CardData(card_id=105, name="Outriders", suit=Suit.ORDER, oath_id="OATH-104"))
_register(CardData(card_id=106, name="Messenger", suit=Suit.ORDER, oath_id="OATH-105"))
_register(CardData(card_id=107, name="Field Promotion", suit=Suit.ORDER, oath_id="OATH-106"))
_register(CardData(card_id=108, name="Palanquin", suit=Suit.ORDER, oath_id="OATH-107"))
_register(CardData(card_id=109, name="Shield Wall", suit=Suit.ORDER, oath_id="OATH-108"))
_register(CardData(card_id=110, name="Military Parade", suit=Suit.ORDER, oath_id="OATH-109"))
_register(CardData(card_id=111, name="Tome Guardians", suit=Suit.ORDER, oath_id="OATH-110"))
_register(CardData(card_id=112, name="Tyrant", suit=Suit.ORDER, oath_id="OATH-111"))
_register(CardData(card_id=113, name="Forced Labor", suit=Suit.ORDER, oath_id="OATH-112"))
_register(CardData(card_id=114, name="Secret Police", suit=Suit.ORDER, oath_id="OATH-113"))
_register(CardData(card_id=115, name="Specialist", suit=Suit.ORDER, oath_id="OATH-114"))
_register(CardData(card_id=116, name="Captains", suit=Suit.ORDER, oath_id="OATH-115"))
_register(CardData(card_id=117, name="Siege Engines", suit=Suit.ORDER, oath_id="OATH-116"))
_register(CardData(card_id=118, name="Royal Tax", suit=Suit.ORDER, oath_id="OATH-117"))
_register(CardData(card_id=119, name="Toll Roads", suit=Suit.ORDER, oath_id="OATH-118"))
_register(CardData(card_id=120, name="Curfew", suit=Suit.ORDER, oath_id="OATH-119"))
_register(CardData(card_id=121, name="Knights Errant", suit=Suit.ORDER, oath_id="OATH-120"))
_register(CardData(card_id=122, name="Vow of Obedience", suit=Suit.ORDER, oath_id="OATH-121"))
_register(CardData(card_id=123, name="Hunting Party", suit=Suit.ORDER, oath_id="OATH-122"))
_register(CardData(card_id=124, name="Council Seat", suit=Suit.ORDER, oath_id="OATH-123"))
_register(CardData(card_id=125, name="Encirclement", suit=Suit.ORDER, oath_id="OATH-124"))
_register(CardData(card_id=126, name="Peace Envoy", suit=Suit.ORDER, oath_id="OATH-125"))
_register(CardData(card_id=127, name="Relic Hunter", suit=Suit.ORDER, oath_id="OATH-126"))
_register(CardData(card_id=128, name="Homesteaders", suit=Suit.HEARTH, oath_id="OATH-127"))
_register(CardData(card_id=129, name="Crop Rotation", suit=Suit.HEARTH, oath_id="OATH-128"))
_register(CardData(card_id=130, name="A Round of Ale", suit=Suit.HEARTH, oath_id="OATH-129"))
_register(CardData(card_id=131, name="Land Warden", suit=Suit.HEARTH, oath_id="OATH-130"))
_register(CardData(card_id=132, name="Charming Friend", suit=Suit.HEARTH, oath_id="OATH-131"))
_register(CardData(card_id=133, name="Village Constable", suit=Suit.HEARTH, oath_id="OATH-132"))
_register(CardData(card_id=134, name="Family Heirloom", suit=Suit.HEARTH, oath_id="OATH-133"))
_register(CardData(card_id=135, name="News from Afar", suit=Suit.HEARTH, oath_id="OATH-134"))
_register(CardData(card_id=136, name="Levelers", suit=Suit.HEARTH, oath_id="OATH-135"))
_register(CardData(card_id=137, name="Fabled Feast", suit=Suit.HEARTH, oath_id="OATH-136"))
_register(CardData(card_id=138, name="The Great Levy", suit=Suit.HEARTH, oath_id="OATH-137"))
_register(CardData(card_id=139, name="Hearts and Minds", suit=Suit.HEARTH, oath_id="OATH-138"))
_register(CardData(card_id=140, name="Relic Breaker", suit=Suit.HEARTH, oath_id="OATH-139"))
_register(CardData(card_id=141, name="Book Binders", suit=Suit.HEARTH, oath_id="OATH-140"))
_register(CardData(card_id=142, name="Ballot Box", suit=Suit.HEARTH, oath_id="OATH-141"))
_register(CardData(card_id=143, name="Saddle Makers", suit=Suit.HEARTH, oath_id="OATH-142"))
_register(CardData(card_id=144, name="Herald", suit=Suit.HEARTH, oath_id="OATH-143"))
_register(CardData(card_id=145, name="Rowdy Pub", suit=Suit.HEARTH, oath_id="OATH-144"))
_register(CardData(card_id=146, name="Vow of Peace", suit=Suit.HEARTH, oath_id="OATH-145"))
_register(CardData(card_id=147, name="Deed Writer", suit=Suit.HEARTH, oath_id="OATH-146"))
_register(CardData(card_id=148, name="Salad Days", suit=Suit.HEARTH, oath_id="OATH-147"))
_register(CardData(card_id=149, name="Marriage", suit=Suit.HEARTH, oath_id="OATH-148"))
_register(CardData(card_id=150, name="Hospital", suit=Suit.HEARTH, oath_id="OATH-149"))
_register(CardData(card_id=151, name="Awaited Return", suit=Suit.HEARTH, oath_id="OATH-150"))
_register(CardData(card_id=152, name="Convoys", suit=Suit.NOMAD, oath_id="OATH-151"))
_register(CardData(card_id=153, name="Vow of Kinship", suit=Suit.NOMAD, oath_id="OATH-152"))
_register(CardData(card_id=154, name="Wild Mounts", suit=Suit.NOMAD, oath_id="OATH-153"))
_register(CardData(card_id=155, name="Lancers", suit=Suit.NOMAD, oath_id="OATH-154"))
_register(CardData(card_id=156, name="Mountain Giant", suit=Suit.NOMAD, oath_id="OATH-155"))
_register(CardData(card_id=157, name="Rival Khan", suit=Suit.NOMAD, oath_id="OATH-156"))
_register(CardData(card_id=158, name="Lost Tongue", suit=Suit.NOMAD, oath_id="OATH-157"))
_register(CardData(card_id=159, name="Special Envoy", suit=Suit.NOMAD, oath_id="OATH-158"))
_register(CardData(card_id=160, name="Resettle", suit=Suit.NOMAD, oath_id="OATH-159"))
_register(CardData(card_id=161, name="Oracle", suit=Suit.NOMAD, oath_id="OATH-160"))
_register(CardData(card_id=162, name="Pilgrimage", suit=Suit.NOMAD, oath_id="OATH-161"))
_register(CardData(card_id=163, name="Spell Breaker", suit=Suit.NOMAD, oath_id="OATH-162"))
_register(CardData(card_id=164, name="Mounted Patrol", suit=Suit.NOMAD, oath_id="OATH-163"))
_register(CardData(card_id=165, name="Great Crusade", suit=Suit.NOMAD, oath_id="OATH-164"))
_register(CardData(card_id=166, name="Ancient Bloodline", suit=Suit.NOMAD, oath_id="OATH-165"))
_register(CardData(card_id=167, name="Ancient Pact", suit=Suit.NOMAD, oath_id="OATH-166"))
_register(CardData(card_id=168, name="Storm Caller", suit=Suit.NOMAD, oath_id="OATH-167"))
_register(CardData(card_id=169, name="Family Wagon", suit=Suit.NOMAD, oath_id="OATH-168"))
_register(CardData(card_id=170, name="Way Station", suit=Suit.NOMAD, oath_id="OATH-169"))
_register(CardData(card_id=171, name="Twin Brother", suit=Suit.NOMAD, oath_id="OATH-170"))
_register(CardData(card_id=172, name="Hospitality", suit=Suit.NOMAD, oath_id="OATH-171"))
_register(CardData(card_id=173, name="A Fast Steed", suit=Suit.NOMAD, oath_id="OATH-172"))
_register(CardData(card_id=174, name="Relic Worship", suit=Suit.NOMAD, oath_id="OATH-173"))
_register(CardData(card_id=175, name="Sacred Ground", suit=Suit.NOMAD, oath_id="OATH-174"))
_register(CardData(card_id=176, name="Nature Worship", suit=Suit.BEAST, oath_id="OATH-175"))
_register(CardData(card_id=177, name="Birdsong", suit=Suit.BEAST, oath_id="OATH-176"))
_register(CardData(card_id=178, name="Small Friends", suit=Suit.BEAST, oath_id="OATH-177"))
_register(CardData(card_id=179, name="Grasping Vines", suit=Suit.BEAST, oath_id="OATH-178"))
_register(CardData(card_id=180, name="Threatening Roar", suit=Suit.BEAST, oath_id="OATH-179"))
_register(CardData(card_id=181, name="Fae Merchant", suit=Suit.BEAST, oath_id="OATH-180"))
_register(CardData(card_id=182, name="Second Chance", suit=Suit.BEAST, oath_id="OATH-181"))
_register(CardData(card_id=183, name="Pied Piper", suit=Suit.BEAST, oath_id="OATH-182"))
_register(CardData(card_id=184, name="Mushrooms", suit=Suit.BEAST, oath_id="OATH-183"))
_register(CardData(card_id=185, name="Insect Swarm", suit=Suit.BEAST, oath_id="OATH-184"))
_register(CardData(card_id=186, name="Vow of Union", suit=Suit.BEAST, oath_id="OATH-185"))
_register(CardData(card_id=187, name="Giant Python", suit=Suit.BEAST, oath_id="OATH-186"))
_register(CardData(card_id=188, name="War Tortoise", suit=Suit.BEAST, oath_id="OATH-187"))
_register(CardData(card_id=189, name="New Growth", suit=Suit.BEAST, oath_id="OATH-188"))
_register(CardData(card_id=190, name="Wild Cry", suit=Suit.BEAST, oath_id="OATH-189"))
_register(CardData(card_id=191, name="Animal Host", suit=Suit.BEAST, oath_id="OATH-190"))
_register(CardData(card_id=192, name="Memory of Nature", suit=Suit.BEAST, oath_id="OATH-191"))
_register(CardData(card_id=193, name="Marsh Spirit", suit=Suit.BEAST, oath_id="OATH-192"))
_register(CardData(card_id=194, name="Vow of Poverty", suit=Suit.BEAST, oath_id="OATH-193"))
_register(CardData(card_id=195, name="Forest Council", suit=Suit.BEAST, oath_id="OATH-194"))
_register(CardData(card_id=196, name="Walled Garden", suit=Suit.BEAST, oath_id="OATH-195"))
_register(CardData(card_id=197, name="Vow of Beastkin", suit=Suit.BEAST, oath_id="OATH-196"))
_register(CardData(card_id=198, name="Bracken", suit=Suit.BEAST, oath_id="OATH-197"))
_register(CardData(card_id=199, name="Wild Allies", suit=Suit.BEAST, oath_id="OATH-198"))

# ── OATH_ID_TO_INTERNAL mapping ──────────────────────────────────
OATH_ID_TO_INTERNAL: dict[str, int] = {
    card.oath_id: card.card_id
    for card in CARD_DB.values()
    if card.oath_id is not None
}


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
    return list(range(1, 200))
