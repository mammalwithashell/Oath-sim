"""Game state renderer for Oath simulator.

Pure rendering functions that take GameState and return strings.
No print() calls — callers decide where output goes.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from oath.enums import (
    Region, Suit, Phase, Role, CompoundStateType, ActionType,
    OathGoal, TitleSide, NUM_ACTIONS,
)
from oath.state.game_state import GameState, CompoundState
from oath.cards.database import get_card
from oath.env.action_decoder import ActionDecoder

_REGION_NAMES = {Region.CRADLE: "Cradle", Region.PROVINCES: "Provinces", Region.HINTERLAND: "Hinterland"}
_SUIT_NAMES = {Suit.DISCORD: "Discord", Suit.ARCANE: "Arcane", Suit.ORDER: "Order",
               Suit.HEARTH: "Hearth", Suit.BEAST: "Beast", Suit.NOMAD: "Nomad"}
_decoder = ActionDecoder()


def _card_str(card_id: Optional[int], show_suit: bool = True) -> str:
    """Format a card ID as 'Name (Suit)' or '--' if None."""
    if card_id is None:
        return "--"
    card = get_card(card_id)
    if card.name == "Padding":
        return "--"
    if show_suit and card.suit is not None:
        return f"{card.name} ({_SUIT_NAMES[card.suit]})"
    return card.name


def _site_name(gs: GameState, site_idx: int) -> str:
    """Get a site's display name."""
    site = gs.sites[site_idx]
    card = get_card(site.site_id)
    if card.name and card.name != "Padding":
        return card.name
    return f"Site {site_idx}"


def render_full_board(gs: GameState, viewer_index: int) -> str:
    """Render the complete board state for display before a player's turn."""
    parts = []
    parts.append(_render_header(gs))
    parts.append(_render_banners_and_favor(gs))
    parts.append(_render_map(gs))
    parts.append(_render_players(gs, viewer_index))
    return "\n".join(parts)


def _render_header(gs: GameState) -> str:
    oath_name = gs.oath_goal.name
    successor_name = gs.successor_goal.name
    ok_holder = f"P{gs.oathkeeper_holder}" if gs.oathkeeper_holder is not None else "none"
    ok_side = gs.oathkeeper_side.name
    lines = [
        "=" * 60,
        f"  OATH OF {oath_name}  |  Round {gs.round_number}/8  |  Successor: {successor_name}",
        f"  Oathkeeper: {ok_holder} ({ok_side} side)",
        "=" * 60,
    ]
    return "\n".join(lines)


def _render_banners_and_favor(gs: GameState) -> str:
    pf = f"P{gs.peoples_favor_holder} ({gs.peoples_favor_tokens} token)" if gs.peoples_favor_holder is not None else f"unclaimed ({gs.peoples_favor_tokens} token)"
    ds = f"P{gs.darkest_secret_holder} ({gs.darkest_secret_tokens} token)" if gs.darkest_secret_holder is not None else f"unclaimed ({gs.darkest_secret_tokens} token)"
    suits = "  ".join(f"{_SUIT_NAMES[Suit(i)]}: {gs.favor_banks[i]}" for i in range(6))
    lines = [
        "",
        "--- BANNERS & FAVOR ---",
        f"  People's Favor: {pf}  |  Darkest Secret: {ds}",
        f"  {suits}",
        f"  Shared secrets: {gs.shared_secrets}  |  World deck: {len(gs.world_deck)}  |  Relic deck: {len(gs.relic_deck)}",
    ]
    return "\n".join(lines)


def _render_map(gs: GameState) -> str:
    lines = ["", "--- MAP ---"]
    for region in (Region.CRADLE, Region.PROVINCES, Region.HINTERLAND):
        region_sites = [(i, s) for i, s in enumerate(gs.sites) if s.region == region]
        if not region_sites:
            continue
        lines.append(f"[{_REGION_NAMES[region].upper()}]")
        for site_idx, site in region_sites:
            name = _site_name(gs, site_idx)
            card_data = get_card(site.site_id)
            defense = card_data.defense if card_data.defense else 0

            if not site.is_faceup:
                lines.append(f"  Site {site_idx}: {name} -- FACEDOWN")
                # Show pawns present even at facedown sites
                pawns = [i for i in range(gs.num_players) if gs.players[i].pawn_site == site_idx]
                if pawns:
                    lines.append(f"    Pawns: {', '.join(f'P{p}' for p in pawns)}")
                continue

            ruler = f"P{site.ruling_player} ({site.warbands} wb)" if site.ruling_player is not None else "unruled"
            lines.append(f"  Site {site_idx}: {name} (def {defense})  Ruler: {ruler}")

            # Cards at site
            card_parts = []
            for slot in range(site.capacity):
                cid = site.cards[slot]
                if cid is not None:
                    card_str = _card_str(cid)
                    extras = []
                    if site.card_favor[slot] > 0:
                        extras.append(f"+{site.card_favor[slot]}f")
                    if site.card_secrets[slot] > 0:
                        extras.append(f"+{site.card_secrets[slot]}s")
                    if extras:
                        card_str += f" {' '.join(extras)}"
                    card_parts.append(f"[{slot}] {card_str}")
                else:
                    card_parts.append(f"[{slot}] --")
            lines.append(f"    {' | '.join(card_parts)}")

            # Relics
            if site.relics:
                relic_names = [_card_str(r, show_suit=False) for r in site.relics]
                lines.append(f"    Relics: {', '.join(relic_names)}")

            # Pawns present
            pawns = [i for i in range(gs.num_players) if gs.players[i].pawn_site == site_idx]
            if pawns:
                pawn_strs = []
                for p in pawns:
                    role = gs.players[p].role.name
                    pawn_strs.append(f"P{p}({role})")
                lines.append(f"    Pawns: {', '.join(pawn_strs)}")

    return "\n".join(lines)


def _render_players(gs: GameState, viewer_index: int) -> str:
    lines = ["", "--- PLAYERS ---"]
    for i in range(gs.num_players):
        p = gs.players[i]
        site_name = _site_name(gs, p.pawn_site)
        is_current = (i == gs.current_player_index)
        is_viewer = (i == viewer_index)

        prefix = ">>> " if is_current else "    "
        suffix = "  <<< YOUR TURN" if (is_current and is_viewer) else ""
        if is_viewer and not is_current:
            suffix = "  (you)"

        lines.append(f"{prefix}P{i} ({p.role.name}) @ {site_name} [site {p.pawn_site}]{suffix}")
        lines.append(f"      Supply: {p.supply}  Favor: {p.favor}  Secrets: {p.secrets}  Warbands: {p.warbands_bank}+{p.warbands_board}")

        # Advisers
        adv_parts = []
        for slot in range(3):
            if p.advisers[slot] is not None:
                # Show card name to viewer, hide others' facedown advisers
                if is_viewer or p.adviser_faceup[slot]:
                    arrow = "^" if p.adviser_faceup[slot] else "v"
                    adv_parts.append(f"[{slot}] {_card_str(p.advisers[slot])} {arrow}")
                else:
                    arrow = "^" if p.adviser_faceup[slot] else "v"
                    if p.adviser_faceup[slot]:
                        adv_parts.append(f"[{slot}] {_card_str(p.advisers[slot])} {arrow}")
                    else:
                        adv_parts.append(f"[{slot}] ??? {arrow}")
        if adv_parts:
            lines.append(f"      Advisers: {' | '.join(adv_parts)}")

        # Relics
        if p.relics:
            if is_viewer:
                relic_names = [_card_str(r, show_suit=False) for r in p.relics]
                lines.append(f"      Relics: {', '.join(relic_names)}")
            else:
                lines.append(f"      Relics: {len(p.relics)} held")

        # Vision
        if p.revealed_vision is not None:
            lines.append(f"      Vision: {_card_str(p.revealed_vision)}")

    return "\n".join(lines)


def render_compound_context(gs: GameState) -> str:
    """Render contextual info for compound action states."""
    cs = gs.compound_state
    if cs is None:
        return ""

    if cs.state_type == CompoundStateType.SEARCH_CHOOSE:
        return _render_search_context(gs, cs)
    elif cs.state_type == CompoundStateType.CAMPAIGN_TARGETS:
        return _render_campaign_targets_context(gs, cs)
    elif cs.state_type == CompoundStateType.CAMPAIGN_BATTLE:
        return _render_campaign_battle_context(gs, cs)
    elif cs.state_type == CompoundStateType.CAMPAIGN_SACRIFICE:
        return _render_campaign_sacrifice_context(gs, cs)
    elif cs.state_type == CompoundStateType.CITIZENSHIP_RESPONSE:
        return _render_citizenship_context(gs, cs)
    elif cs.state_type == CompoundStateType.RELIQUARY_CHOOSE:
        return _render_reliquary_context(gs, cs)
    return ""


def _render_search_context(gs: GameState, cs: CompoundState) -> str:
    source = cs.search_source or "unknown"
    lines = [f"\n--- SEARCH RESULTS (from {source}) ---"]
    for i, remaining in enumerate(cs.cards_remaining):
        if i < len(cs.drawn_cards):
            card_id = cs.drawn_cards[i]
            status = "" if remaining else " [already placed]"
            lines.append(f"  [{i}] {_card_str(card_id)}{status}")
    return "\n".join(lines)


def _render_campaign_targets_context(gs: GameState, cs: CompoundState) -> str:
    attacker = cs.campaign_attacker
    defender = cs.campaign_defender
    lines = [f"\n--- CAMPAIGN: P{attacker} attacking P{defender} ---"]
    if cs.campaign_targets:
        target_strs = []
        for t in cs.campaign_targets:
            if t.startswith("site:"):
                si = int(t.split(":")[1])
                target_strs.append(f"{_site_name(gs, si)} [site {si}]")
            elif t.startswith("relic:"):
                ri = int(t.split(":")[1])
                if defender is not None and ri < len(gs.players[defender].relics):
                    target_strs.append(f"relic: {_card_str(gs.players[defender].relics[ri], show_suit=False)}")
                else:
                    target_strs.append(t)
            elif t == "pawn":
                target_strs.append("pawn (banish)")
        lines.append(f"  Current targets: {', '.join(target_strs)}")
    else:
        lines.append("  No targets selected yet.")
    return "\n".join(lines)


def _render_campaign_battle_context(gs: GameState, cs: CompoundState) -> str:
    lines = [
        f"\n--- CAMPAIGN BATTLE ---",
        f"  Attack dice: {cs.campaign_attack_dice}  |  Defense dice: {cs.campaign_defense_dice}",
        f"  Choose a battle plan card or skip.",
    ]
    return "\n".join(lines)


def _render_campaign_sacrifice_context(gs: GameState, cs: CompoundState) -> str:
    deficit = cs.campaign_defense_result - cs.campaign_attack_result
    attacker = cs.campaign_attacker
    wb = gs.players[attacker].warbands_board if attacker is not None else 0
    lines = [
        f"\n--- CAMPAIGN SACRIFICE ---",
        f"  You lost the dice roll by {deficit}.",
        f"  Sacrifice warbands to force the campaign through?",
        f"  Warbands available: {wb}",
    ]
    return "\n".join(lines)


def _render_citizenship_context(gs: GameState, cs: CompoundState) -> str:
    offerer = cs.citizenship_offerer
    lines = [
        f"\n--- CITIZENSHIP OFFER ---",
        f"  P{offerer} is offering you citizenship.",
        f"  Accept to become a Citizen, or decline.",
    ]
    return "\n".join(lines)


def _render_reliquary_context(gs: GameState, cs: CompoundState) -> str:
    lines = ["\n--- RELIQUARY ---", "  Choose a relic:"]
    for i, relic_id in enumerate(gs.reliquary):
        lines.append(f"  [{i}] {_card_str(relic_id, show_suit=False)}")
    if not gs.reliquary:
        lines.append("  (empty)")
    return "\n".join(lines)


def render_action_menu(gs: GameState, player_index: int, action_mask: np.ndarray) -> tuple[str, dict[int, int]]:
    """Render numbered action menu from legal action mask.

    Returns:
        Tuple of (display_string, menu_map) where menu_map maps
        menu number (1-based) to action ID.
    """
    # Filter out communication actions (102-118) — noise for human players
    legal_actions = [i for i in range(NUM_ACTIONS)
                     if action_mask[i] > 0.5 and not (102 <= i <= 118)]

    # Deduplicate actions that map to the same absolute target
    seen_descriptions: set[str] = set()
    menu_map: dict[int, int] = {}
    lines = ["\n--- ACTIONS ---"]
    menu_num = 0

    for action_id in legal_actions:
        desc = describe_action(action_id, gs, player_index)
        if desc in seen_descriptions:
            continue
        seen_descriptions.add(desc)
        menu_num += 1
        lines.append(f"  [{menu_num}] {desc}")
        menu_map[menu_num] = action_id

    return "\n".join(lines), menu_map


def describe_action(action_id: int, gs: GameState, player_index: int) -> str:
    """Human-readable description of a single action."""
    decoded = _decoder.decode(action_id)
    at = decoded.action_type
    player = gs.players[player_index]
    site = gs.sites[player.pawn_site]

    if at == ActionType.TRAVEL:
        si = decoded.site_index
        name = _site_name(gs, si)
        region = _REGION_NAMES[gs.sites[si].region]
        return f"Travel to {name} [site {si}, {region}]"

    elif at == ActionType.SEARCH:
        source = decoded.search_destination
        return f"Search the {source}"

    elif at == ActionType.MUSTER:
        slot = decoded.card_slot
        cid = site.cards[slot] if slot < len(site.cards) else None
        return f"Muster: {_card_str(cid)} [slot {slot}]"

    elif at == ActionType.TRADE_FAVOR:
        slot = decoded.card_slot
        cid = site.cards[slot] if slot < len(site.cards) else None
        return f"Trade for favor: {_card_str(cid)} [slot {slot}]"

    elif at == ActionType.TRADE_SECRETS:
        slot = decoded.card_slot
        cid = site.cards[slot] if slot < len(site.cards) else None
        return f"Trade for secrets: {_card_str(cid)} [slot {slot}]"

    elif at == ActionType.RECOVER:
        slot = decoded.target_relic_slot
        if slot is not None and slot < len(site.relics):
            return f"Recover relic: {_card_str(site.relics[slot], show_suit=False)} [slot {slot}]"
        return f"Recover relic [slot {slot}]"

    elif at == ActionType.RECOVER_PEOPLES_FAVOR:
        return "Recover People's Favor"

    elif at == ActionType.RECOVER_DARKEST_SECRET:
        return "Recover Darkest Secret"

    elif at == ActionType.CAMPAIGN_DECLARE:
        rel = decoded.target_player
        abs_target = (player_index + rel) % gs.num_players
        target_role = gs.players[abs_target].role.name
        return f"Campaign against P{abs_target} ({target_role})"

    elif at == ActionType.MINOR_FLIP_ADVISER:
        slot = decoded.card_slot
        cid = player.advisers[slot] if slot < len(player.advisers) else None
        return f"Flip adviser: {_card_str(cid)} [slot {slot}]"

    elif at == ActionType.MINOR_USE_ACTION:
        slot = decoded.card_slot
        # Slots 0-2 are advisers, 3-5 are site cards
        if slot < 3:
            cid = player.advisers[slot] if slot < len(player.advisers) else None
            return f"Use action: {_card_str(cid)} [adviser {slot}]"
        else:
            site_slot = slot - 3
            cid = site.cards[site_slot] if site_slot < len(site.cards) else None
            return f"Use action: {_card_str(cid)} [site slot {site_slot}]"

    elif at == ActionType.END_ACT_PHASE:
        return "End act phase"

    elif at == ActionType.OFFER_CITIZENSHIP:
        rel = decoded.target_player
        abs_target = (player_index + rel) % gs.num_players
        return f"Offer citizenship to P{abs_target}"

    elif at == ActionType.ACCEPT_CITIZENSHIP:
        return "Accept citizenship"

    elif at == ActionType.DECLINE_CITIZENSHIP:
        return "Decline citizenship"

    elif at == ActionType.SELF_EXILE:
        return "Self-exile (become Exile)"

    elif at == ActionType.RELIQUARY_CHOOSE:
        slot = decoded.card_slot
        if slot is not None and slot < len(gs.reliquary):
            return f"Take relic: {_card_str(gs.reliquary[slot], show_suit=False)} [slot {slot}]"
        return f"Take relic [slot {slot}]"

    elif at == ActionType.CAMPAIGN_BATTLE_PLAN:
        slot = decoded.card_slot
        cid = player.advisers[slot] if slot < len(player.advisers) else None
        return f"Battle plan: {_card_str(cid)} [adviser {slot}]"

    elif at == ActionType.CAMPAIGN_NO_BATTLE:
        return "Skip battle plan"

    elif at == ActionType.CAMPAIGN_SACRIFICE:
        count = decoded.sacrifice_count
        return f"Sacrifice {count} warband{'s' if count != 1 else ''}"

    elif at == ActionType.SEARCH_PLAY:
        ci = decoded.search_card_index
        dest = decoded.search_destination
        cs = gs.compound_state
        if cs and ci is not None and ci < len(cs.drawn_cards):
            cid = cs.drawn_cards[ci]
            card_name = _card_str(cid)
        else:
            card_name = f"card {ci}"
        dest_names = {"site": "to site", "adviser_up": "as adviser (faceup)", "adviser_down": "as adviser (facedown)"}
        return f"Play {card_name} {dest_names.get(dest, dest)}"

    elif at == ActionType.SEARCH_DISCARD:
        ci = decoded.search_card_index
        cs = gs.compound_state
        if cs and ci is not None and ci < len(cs.drawn_cards):
            cid = cs.drawn_cards[ci]
            card_name = _card_str(cid)
        else:
            card_name = f"card {ci}"
        return f"Discard {card_name}"

    elif at == ActionType.CAMPAIGN_DONE_TARGETS:
        return "Done selecting targets"

    elif at == ActionType.CAMPAIGN_TARGET_SITE:
        si = decoded.site_index
        return f"Target site: {_site_name(gs, si)} [site {si}]"

    elif at == ActionType.CAMPAIGN_TARGET_RELIC:
        slot = decoded.target_relic_slot
        cs = gs.compound_state
        if cs and cs.campaign_defender is not None and slot is not None:
            defender = gs.players[cs.campaign_defender]
            if slot < len(defender.relics):
                return f"Target relic: {_card_str(defender.relics[slot], show_suit=False)}"
        return f"Target relic [slot {slot}]"

    elif at == ActionType.CAMPAIGN_TARGET_PAWN:
        return "Target pawn (banish)"

    elif at == ActionType.COMM_SIGNAL:
        return f"Send signal {decoded.signal_type}"

    elif at == ActionType.COMM_TARGET:
        return f"Signal target {decoded.signal_target}"

    return f"Action {action_id}"
