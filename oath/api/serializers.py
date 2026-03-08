"""Serialize GameState to JSON-friendly dicts for the web frontend."""

from __future__ import annotations

from typing import Optional

import numpy as np

from oath.cards.database import get_card
from oath.display.renderer import describe_action
from oath.enums import NUM_ACTIONS, Suit, ActionType
from oath.env.action_decoder import ActionDecoder
from oath.state.game_state import GameState

_SUIT_NAMES = {
    Suit.DISCORD: "Discord",
    Suit.ARCANE: "Arcane",
    Suit.ORDER: "Order",
    Suit.HEARTH: "Hearth",
    Suit.BEAST: "Beast",
    Suit.NOMAD: "Nomad",
}

_decoder = ActionDecoder()


def serialize_card(card_id: Optional[int]) -> Optional[dict]:
    """Resolve a card ID to a JSON-friendly dict."""
    if card_id is None:
        return None
    card = get_card(card_id)
    if card.name == "Empty" or card.name == "Padding":
        return None
    return {
        "id": card.card_id,
        "name": card.name,
        "suit": _SUIT_NAMES[card.suit] if card.suit is not None else None,
        "is_vision": card.is_vision,
        "is_relic": card.is_relic,
        "is_site": card.is_site,
        "is_edifice": card.is_edifice,
    }


def serialize_game_state(gs: GameState, viewer_index: int) -> dict:
    """Serialize full game state for a specific viewer."""
    return {
        "round_number": gs.round_number,
        "phase": gs.phase.name,
        "oath_goal": gs.oath_goal.name,
        "successor_goal": gs.successor_goal.name,
        "current_player_index": gs.current_player_index,
        "num_players": gs.num_players,
        "is_game_over": gs.is_game_over,
        "winner": gs.winner,
        "win_type": gs.win_type.name if gs.win_type else None,
        "oathkeeper_holder": gs.oathkeeper_holder,
        "oathkeeper_side": gs.oathkeeper_side.name,
        "peoples_favor": {
            "holder": gs.peoples_favor_holder,
            "tokens": gs.peoples_favor_tokens,
        },
        "darkest_secret": {
            "holder": gs.darkest_secret_holder,
            "tokens": gs.darkest_secret_tokens,
        },
        "favor_banks": {
            _SUIT_NAMES[Suit(i)]: gs.favor_banks[i] for i in range(6)
        },
        "shared_secrets": gs.shared_secrets,
        "world_deck_size": len(gs.world_deck),
        "relic_deck_size": len(gs.relic_deck),
        "sites": [_serialize_site(gs, i) for i in range(len(gs.sites))],
        "players": [
            _serialize_player(gs, i, viewer_index)
            for i in range(gs.num_players)
        ],
        "compound_state": _serialize_compound(gs),
    }


def _serialize_site(gs: GameState, site_idx: int) -> dict:
    site = gs.sites[site_idx]
    card_data = get_card(site.site_id)

    cards = []
    for slot in range(site.capacity):
        cid = site.cards[slot]
        if cid is not None:
            card_info = serialize_card(cid)
            if card_info:
                card_info["favor"] = site.card_favor[slot]
                card_info["secrets"] = site.card_secrets[slot]
                cards.append(card_info)
            else:
                cards.append(None)
        else:
            cards.append(None)

    pawns = [
        i for i in range(gs.num_players)
        if gs.players[i].pawn_site == site_idx
    ]

    return {
        "index": site_idx,
        "name": card_data.name if card_data.name != "Empty" else f"Site {site_idx}",
        "region": site.region.name,
        "defense": card_data.defense,
        "is_faceup": site.is_faceup,
        "capacity": site.capacity,
        "ruling_player": site.ruling_player,
        "warbands": site.warbands,
        "cards": cards,
        "relics": [serialize_card(r) for r in site.relics],
        "pawns": pawns,
    }


def _serialize_player(gs: GameState, player_idx: int, viewer_idx: int) -> dict:
    p = gs.players[player_idx]
    is_viewer = player_idx == viewer_idx
    site_data = get_card(gs.sites[p.pawn_site].site_id)

    advisers = []
    for slot in range(3):
        if p.advisers[slot] is not None:
            if is_viewer or p.adviser_faceup[slot]:
                info = serialize_card(p.advisers[slot])
                if info:
                    info["faceup"] = p.adviser_faceup[slot]
                    info["slot"] = slot
                    advisers.append(info)
            else:
                advisers.append({
                    "id": None,
                    "name": "???",
                    "suit": None,
                    "faceup": p.adviser_faceup[slot],
                    "slot": slot,
                    "is_vision": False,
                    "is_relic": False,
                    "is_site": False,
                    "is_edifice": False,
                })

    relics = []
    if is_viewer:
        relics = [serialize_card(r) for r in p.relics]
    else:
        relics = [{"id": None, "name": "Hidden Relic"} for _ in p.relics]

    vision = None
    if p.revealed_vision is not None:
        vision = serialize_card(p.revealed_vision)

    return {
        "index": player_idx,
        "role": p.role.name,
        "pawn_site": p.pawn_site,
        "site_name": site_data.name if site_data.name != "Empty" else f"Site {p.pawn_site}",
        "supply": p.supply,
        "favor": p.favor,
        "secrets": p.secrets,
        "warbands_bank": p.warbands_bank,
        "warbands_board": p.warbands_board,
        "advisers": advisers,
        "relics": relics,
        "vision": vision,
        "num_sites_ruled": gs.count_sites_ruled(player_idx),
    }


def _serialize_compound(gs: GameState) -> Optional[dict]:
    cs = gs.compound_state
    if cs is None:
        return None

    result: dict = {"state_type": cs.state_type.name}

    # Search
    if cs.drawn_cards:
        result["drawn_cards"] = []
        for i, cid in enumerate(cs.drawn_cards):
            card_info = serialize_card(cid)
            if card_info:
                card_info["remaining"] = cs.cards_remaining[i] if i < len(cs.cards_remaining) else False
                result["drawn_cards"].append(card_info)
        result["search_source"] = cs.search_source

    # Campaign
    if cs.campaign_attacker is not None:
        result["campaign_attacker"] = cs.campaign_attacker
        result["campaign_defender"] = cs.campaign_defender
        result["campaign_targets"] = cs.campaign_targets
        result["campaign_attack_dice"] = cs.campaign_attack_dice
        result["campaign_defense_dice"] = cs.campaign_defense_dice
        result["campaign_attack_result"] = cs.campaign_attack_result
        result["campaign_defense_result"] = cs.campaign_defense_result

    # Citizenship
    if cs.citizenship_offerer is not None:
        result["citizenship_offerer"] = cs.citizenship_offerer
        result["citizenship_target"] = cs.citizenship_target

    return result


def serialize_legal_actions(
    gs: GameState, player_index: int, action_mask: np.ndarray
) -> list[dict]:
    """Convert action mask to list of legal actions with descriptions."""
    actions = []
    for action_id in range(NUM_ACTIONS):
        if action_mask[action_id] < 0.5:
            continue
        if 102 <= action_id <= 118:
            continue  # Skip communication signals

        decoded = _decoder.decode(action_id)
        desc = describe_action(action_id, gs, player_index)
        actions.append({
            "action_id": action_id,
            "action_type": decoded.action_type.name,
            "description": desc,
        })

    return actions
