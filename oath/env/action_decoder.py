"""Action ID → game action decoder for Oath simulator.

Maps integer action IDs (0–122) to concrete game actions and
computes legal action masks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from oath.enums import (
    ActionType, Phase, CompoundStateType, Role, CardRestriction, OathGoal,
    MAX_SITES, MAX_CARDS_PER_SITE, MAX_ADVISERS, MAX_PLAYERS,
    MAX_RELICS_PER_SITE, MAX_RELIQUARY, NUM_ACTIONS,
    VISION_TO_OATH_GOAL,
)
from oath.state.game_state import GameState
from oath.cards.database import get_card


@dataclass
class DecodedAction:
    """Concrete game action after decoding an action ID."""
    action_type: ActionType
    site_index: Optional[int] = None
    card_slot: Optional[int] = None
    target_player: Optional[int] = None
    target_relic_slot: Optional[int] = None
    sacrifice_count: Optional[int] = None
    search_card_index: Optional[int] = None
    search_destination: Optional[str] = None
    signal_type: Optional[int] = None
    signal_target: Optional[int] = None


class ActionDecoder:
    """Decodes integer action IDs to concrete game actions."""

    def decode(self, action_id: int) -> DecodedAction:
        """Convert action ID (0–122) to DecodedAction."""
        if action_id < 0 or action_id >= NUM_ACTIONS:
            raise ValueError(f"Invalid action ID: {action_id}")

        # TRAVEL (0–7)
        if 0 <= action_id <= 7:
            return DecodedAction(ActionType.TRAVEL, site_index=action_id)

        # SEARCH (8–9)
        if 8 <= action_id <= 9:
            source = "deck" if action_id == 8 else "discard"
            return DecodedAction(ActionType.SEARCH, search_destination=source)

        # MUSTER (10–12)
        if 10 <= action_id <= 12:
            return DecodedAction(ActionType.MUSTER, card_slot=action_id - 10)

        # TRADE_FAVOR (13–15)
        if 13 <= action_id <= 15:
            return DecodedAction(ActionType.TRADE_FAVOR, card_slot=action_id - 13)

        # TRADE_SECRETS (16–18)
        if 16 <= action_id <= 18:
            return DecodedAction(ActionType.TRADE_SECRETS, card_slot=action_id - 16)

        # RECOVER (19–23)
        if 19 <= action_id <= 23:
            slot = action_id - 19
            if slot <= 2:
                return DecodedAction(ActionType.RECOVER, target_relic_slot=slot)
            elif slot == 3:
                return DecodedAction(action_type=ActionType.RECOVER_PEOPLES_FAVOR)
            else:
                return DecodedAction(action_type=ActionType.RECOVER_DARKEST_SECRET)

        # CAMPAIGN_DECLARE (24–28)
        if 24 <= action_id <= 28:
            return DecodedAction(ActionType.CAMPAIGN_DECLARE,
                                target_player=action_id - 24 + 1)

        # MINOR_FLIP_ADVISER (29–31)
        if 29 <= action_id <= 31:
            return DecodedAction(ActionType.MINOR_FLIP_ADVISER,
                                card_slot=action_id - 29)

        # MINOR_USE_ACTION (32–37)
        if 32 <= action_id <= 37:
            return DecodedAction(ActionType.MINOR_USE_ACTION,
                                card_slot=action_id - 32)

        # MINOR_WARBANDS (38–39)
        if 38 <= action_id <= 39:
            return DecodedAction(ActionType.MINOR_WARBANDS,
                                card_slot=action_id - 38)

        # MINOR_PEEK_RELIC (40–42)
        if 40 <= action_id <= 42:
            return DecodedAction(ActionType.MINOR_PEEK_RELIC,
                                target_relic_slot=action_id - 40)

        # END_ACT_PHASE (43)
        if action_id == 43:
            return DecodedAction(ActionType.END_ACT_PHASE)

        # OFFER_CITIZENSHIP (44–48)
        if 44 <= action_id <= 48:
            return DecodedAction(ActionType.OFFER_CITIZENSHIP,
                                target_player=action_id - 44 + 1)

        # ACCEPT_CITIZENSHIP (49)
        if action_id == 49:
            return DecodedAction(ActionType.ACCEPT_CITIZENSHIP)

        # DECLINE_CITIZENSHIP (50)
        if action_id == 50:
            return DecodedAction(ActionType.DECLINE_CITIZENSHIP)

        # SELF_EXILE (51)
        if action_id == 51:
            return DecodedAction(ActionType.SELF_EXILE)

        # RELIQUARY_CHOOSE (52–55)
        if 52 <= action_id <= 55:
            return DecodedAction(ActionType.RELIQUARY_CHOOSE,
                                card_slot=action_id - 52)

        # CAMPAIGN_BATTLE_PLAN (56–58)
        if 56 <= action_id <= 58:
            return DecodedAction(ActionType.CAMPAIGN_BATTLE_PLAN,
                                card_slot=action_id - 56)

        # CAMPAIGN_NO_BATTLE (59)
        if action_id == 59:
            return DecodedAction(ActionType.CAMPAIGN_NO_BATTLE)

        # CAMPAIGN_SACRIFICE (60–65)
        if 60 <= action_id <= 65:
            return DecodedAction(ActionType.CAMPAIGN_SACRIFICE,
                                sacrifice_count=action_id - 60)

        # SEARCH_PLAY (66–80): card[0..4] × dest[site, adviser_up, adviser_down]
        if 66 <= action_id <= 80:
            idx = action_id - 66
            card_index = idx // 3
            dest_index = idx % 3
            destinations = ["site", "adviser_up", "adviser_down"]
            return DecodedAction(ActionType.SEARCH_PLAY,
                                search_card_index=card_index,
                                search_destination=destinations[dest_index])

        # SEARCH_DISCARD (81–85)
        if 81 <= action_id <= 85:
            return DecodedAction(ActionType.SEARCH_DISCARD,
                                search_card_index=action_id - 81)

        # CAMPAIGN_DECLARE_BANDITS (86)
        if action_id == 86:
            return DecodedAction(ActionType.CAMPAIGN_DECLARE_BANDITS)

        # CAMPAIGN_DONE_TARGETS (87)
        if action_id == 87:
            return DecodedAction(ActionType.CAMPAIGN_DONE_TARGETS)

        # CAMPAIGN_TARGET_SITE (88–95)
        if 88 <= action_id <= 95:
            return DecodedAction(ActionType.CAMPAIGN_TARGET_SITE,
                                site_index=action_id - 88)

        # CAMPAIGN_TARGET_RELIC (96–100)
        if 96 <= action_id <= 100:
            return DecodedAction(ActionType.CAMPAIGN_TARGET_RELIC,
                                target_relic_slot=action_id - 96)

        # CAMPAIGN_TARGET_PAWN (101)
        if action_id == 101:
            return DecodedAction(ActionType.CAMPAIGN_TARGET_PAWN)

        # COMM_SIGNAL (102–109)
        if 102 <= action_id <= 109:
            return DecodedAction(ActionType.COMM_SIGNAL,
                                signal_type=action_id - 102)

        # COMM_TARGET (110–118)
        if 110 <= action_id <= 118:
            return DecodedAction(ActionType.COMM_TARGET,
                                signal_target=action_id - 110)

        # VOW (119–122)
        if action_id == 119:
            return DecodedAction(ActionType.VOW_SUPREMACY)
        if action_id == 120:
            return DecodedAction(ActionType.VOW_PEOPLE)
        if action_id == 121:
            return DecodedAction(ActionType.VOW_DEVOTION)
        if action_id == 122:
            return DecodedAction(ActionType.VOW_SANCTUARY)

        # CAMPAIGN_PLACE_WARBANDS (123–131): place 0–8 warbands on targeted site
        if 123 <= action_id <= 131:
            return DecodedAction(ActionType.CAMPAIGN_PLACE_WARBANDS,
                                sacrifice_count=action_id - 123)

        # EXILE_CITIZEN (132–136): target relative players 1–5
        if 132 <= action_id <= 136:
            return DecodedAction(ActionType.EXILE_CITIZEN,
                                target_player=action_id - 132 + 1)

        raise ValueError(f"Unhandled action ID: {action_id}")

    def get_legal_mask(self, gs: GameState, player_index: int) -> np.ndarray:
        """Compute binary mask of legal actions for the given player."""
        mask = np.zeros(NUM_ACTIONS, dtype=np.float32)

        # Vow phase: only VOW actions are legal for the winner
        if gs.in_vow_phase:
            return self._get_vow_mask(gs, player_index)

        player = gs.players[player_index]

        # If in a compound state, only that state's actions are legal
        if gs.compound_state is not None:
            return self._get_compound_mask(gs, player_index)

        if gs.phase == Phase.WAKE:
            # During wake, only action is to proceed to act phase
            # We auto-advance, so provide END_ACT as a pass-through
            # Actually wake is automated; if we're asked for actions during wake,
            # just allow ending (auto-transition to act)
            mask[43] = 1.0  # END_ACT_PHASE to signal "ready"
            return mask

        if gs.phase != Phase.ACT:
            mask[43] = 1.0
            return mask

        from oath.engine.actions import (
            can_travel, can_muster, can_trade_favor, can_trade_secrets,
            can_search_deck, can_search_discard, can_recover_relic,
            can_recover_peoples_favor, can_recover_darkest_secret,
            can_flip_adviser, can_use_card_action, can_offer_citizenship,
            can_self_exile, can_exile_citizen,
            can_move_warbands_to_board, can_move_warbands_to_site,
        )
        from oath.engine.campaign import can_campaign, can_campaign_bandits

        # Travel (0–7)
        for site_idx in range(MAX_SITES):
            if can_travel(gs, player_index, site_idx):
                mask[site_idx] = 1.0

        # Search (8–9)
        if can_search_deck(gs, player_index):
            mask[8] = 1.0
        if can_search_discard(gs, player_index):
            mask[9] = 1.0

        # Muster (10–12)
        for slot in range(MAX_CARDS_PER_SITE):
            if can_muster(gs, player_index, slot):
                mask[10 + slot] = 1.0

        # Trade favor (13–15)
        for slot in range(MAX_CARDS_PER_SITE):
            if can_trade_favor(gs, player_index, slot):
                mask[13 + slot] = 1.0

        # Trade secrets (16–18)
        for slot in range(MAX_CARDS_PER_SITE):
            if can_trade_secrets(gs, player_index, slot):
                mask[16 + slot] = 1.0

        # Recover (19–23)
        for slot in range(3):
            if can_recover_relic(gs, player_index, slot):
                mask[19 + slot] = 1.0
        if can_recover_peoples_favor(gs, player_index):
            mask[22] = 1.0
        if can_recover_darkest_secret(gs, player_index):
            mask[23] = 1.0

        # Campaign (24–28): target players
        for rel_player in range(1, 6):
            abs_player = (player_index + rel_player) % gs.num_players
            if abs_player != player_index and can_campaign(gs, player_index, abs_player):
                mask[24 + rel_player - 1] = 1.0

        # Campaign bandits (86): target bandits at unruled site
        if can_campaign_bandits(gs, player_index):
            mask[86] = 1.0

        # Minor: flip adviser (29–31)
        for slot in range(MAX_ADVISERS):
            if can_flip_adviser(gs, player_index, slot):
                mask[29 + slot] = 1.0

        # Minor: use card action (32–37)
        for source in range(6):
            if can_use_card_action(gs, player_index, source):
                mask[32 + source] = 1.0

        # Minor: move warbands (38–39)
        if can_move_warbands_to_board(gs, player_index):
            mask[38] = 1.0
        if can_move_warbands_to_site(gs, player_index):
            mask[39] = 1.0

        # End act phase (43) — always legal during act
        mask[43] = 1.0

        # Citizenship (44–48)
        for rel in range(1, 6):
            abs_target = (player_index + rel) % gs.num_players
            if abs_target != player_index and can_offer_citizenship(gs, player_index, abs_target):
                mask[44 + rel - 1] = 1.0

        # Self-exile (51)
        if can_self_exile(gs, player_index):
            mask[51] = 1.0

        # Exile citizen (132–136): target relative players 1–5
        for rel_player in range(1, 6):
            abs_player = (player_index + rel_player) % gs.num_players
            if abs_player != player_index and can_exile_citizen(gs, player_index, abs_player):
                mask[132 + rel_player - 1] = 1.0

        # Communication (102–118) — always legal during act
        for i in range(8):
            mask[102 + i] = 1.0

        return mask

    def _get_compound_mask(self, gs: GameState, player_index: int) -> np.ndarray:
        """Get legal mask during compound action states."""
        mask = np.zeros(NUM_ACTIONS, dtype=np.float32)
        cs = gs.compound_state
        if cs is None:
            return mask

        if cs.state_type == CompoundStateType.SEARCH_CHOOSE:
            # SEARCH_PLAY (66–80) and SEARCH_DISCARD (81–85)
            player = gs.players[player_index]
            site = gs.sites[player.pawn_site]

            for i, remaining in enumerate(cs.cards_remaining):
                if not remaining or i >= 5:
                    continue
                card_id = cs.drawn_cards[i]
                card_data = get_card(card_id)

                # Play to site
                # People's Favor holder can also play to full sites (auto-discard)
                has_pf = gs.peoples_favor_holder == player_index
                site_has_room = site.has_empty_card_slot() or has_pf
                if (card_data.restriction != CardRestriction.ADVISER_ONLY and
                        site_has_room):
                    mask[66 + i * 3 + 0] = 1.0  # site

                # Play as adviser (up/down)
                if card_data.restriction != CardRestriction.SITE_ONLY:
                    has_empty = player.first_empty_adviser_slot() is not None
                    if has_empty:
                        has_slot = True
                    else:
                        # All slots full: check if at least one non-LOCKED adviser
                        has_slot = False
                        for _s in range(MAX_ADVISERS):
                            if player.advisers[_s] is not None:
                                _adv = get_card(player.advisers[_s])
                                if _adv.restriction != CardRestriction.LOCKED:
                                    has_slot = True
                                    break
                    if has_slot:
                        mask[66 + i * 3 + 1] = 1.0  # adviser_up
                        mask[66 + i * 3 + 2] = 1.0  # adviser_down

                # Visions can only be kept (played as vision)
                if card_data.is_vision:
                    mask[66 + i * 3 + 1] = 1.0  # adviser_up acts as "keep vision"

                # Discard
                mask[81 + i] = 1.0

            # Must play at least one card, so if only one remaining, force play
            remaining_count = sum(1 for r in cs.cards_remaining if r)
            if remaining_count == 0:
                # Shouldn't happen, but safety
                pass

        elif cs.state_type == CompoundStateType.CAMPAIGN_TARGETS:
            # §5.5.2: Declare targets and collect dice pools
            player = gs.players[player_index]
            defender = cs.campaign_defender

            if defender == -1:
                # Bandit campaign: only target is attacker's site
                pawn_site = player.pawn_site
                if f"site:{pawn_site}" not in cs.campaign_targets:
                    mask[88 + pawn_site] = 1.0
                # Done targets — always available once site is targeted
                if cs.campaign_targets:
                    mask[87] = 1.0
            elif defender is not None and defender >= 0:
                defender_player = gs.players[defender]
                defender_at_attacker_site = (
                    defender_player.pawn_site == player.pawn_site
                )
                attacker_site_ruled_by_defender = (
                    gs.sites[player.pawn_site].ruling_player == defender
                )

                # Site targets: any site ruled by defender, anywhere on map
                for site_idx in range(MAX_SITES):
                    site = gs.sites[site_idx]
                    if site.ruling_player == defender:
                        if f"site:{site_idx}" not in cs.campaign_targets:
                            mask[88 + site_idx] = 1.0

                # Relic targets: only if defender's pawn is at attacker's site
                if defender_at_attacker_site:
                    for slot in range(min(5, len(defender_player.relics))):
                        if f"relic:{slot}" not in cs.campaign_targets:
                            mask[96 + slot] = 1.0

                # Pawn target: only if defender's pawn is at attacker's site
                if defender_at_attacker_site:
                    if "pawn" not in cs.campaign_targets:
                        mask[101] = 1.0

                # Done targets (87) — must have at least one target
                # §5.5.2: if defender rules your site, you must target your site
                if cs.campaign_targets:
                    if gs.sites[player.pawn_site].ruling_player == defender:
                        # Must include attacker's site before finishing
                        if f"site:{player.pawn_site}" in cs.campaign_targets:
                            mask[87] = 1.0
                    else:
                        mask[87] = 1.0

        elif cs.state_type == CompoundStateType.CAMPAIGN_BATTLE:
            # Attacker battle plan cards (56–58)
            player = gs.players[player_index]
            from oath.cards.effects import get_battle_plan_effects
            for slot in range(MAX_ADVISERS):
                if (player.advisers[slot] is not None and
                        player.adviser_faceup[slot]):
                    effects = get_battle_plan_effects(player.advisers[slot])
                    if effects:
                        mask[56 + slot] = 1.0

            # No battle plan (59) — always legal
            mask[59] = 1.0

        elif cs.state_type == CompoundStateType.CAMPAIGN_BATTLE_DEFENDER:
            # §5.5.3: Defender battle plan cards (56–58)
            # Bandits (defender == -1) should never reach this state,
            # but guard against it just in case.
            defender = cs.campaign_defender
            if defender is not None and defender >= 0:
                defender_player = gs.players[defender]
                from oath.cards.effects import get_battle_plan_effects
                for slot in range(MAX_ADVISERS):
                    if (defender_player.advisers[slot] is not None and
                            defender_player.adviser_faceup[slot]):
                        effects = get_battle_plan_effects(
                            defender_player.advisers[slot])
                        if effects:
                            mask[56 + slot] = 1.0

            # No battle plan (59) — always legal
            mask[59] = 1.0

        elif cs.state_type == CompoundStateType.CAMPAIGN_SACRIFICE:
            # Per §5.5.5: either decline (0 = accept defeat) or sacrifice
            # exactly enough to win (attack must strictly exceed defense)
            mask[60] = 1.0  # Sacrifice 0 = decline, accept defeat
            deficit = cs.campaign_defense_result - cs.campaign_attack_result
            needed = deficit + 1  # Must exceed, not just tie
            player = gs.players[player_index]
            if needed <= min(player.warbands_board, 5):
                mask[60 + needed] = 1.0

        elif cs.state_type == CompoundStateType.RELIQUARY_CHOOSE:
            # Reliquary slots (52–55)
            for slot in range(min(MAX_RELIQUARY, len(gs.reliquary))):
                mask[52 + slot] = 1.0
            # If reliquary is empty, still allow slot 0 as "no relic"
            if not gs.reliquary:
                mask[52] = 1.0

        elif cs.state_type == CompoundStateType.CITIZENSHIP_RESPONSE:
            mask[49] = 1.0  # Accept
            mask[50] = 1.0  # Decline

        elif cs.state_type == CompoundStateType.CAMPAIGN_BANISH_TRAVEL:
            # §5.5.7.III: Attacker chooses destination site or skips
            from oath.engine.campaign import can_banish_travel_to
            mask[59] = 1.0  # Skip travel (CAMPAIGN_NO_BATTLE reused)
            if cs.banish_target is not None:
                for site_idx in range(MAX_SITES):
                    if can_banish_travel_to(gs, cs.banish_target, site_idx):
                        mask[site_idx] = 1.0  # TRAVEL IDs 0-7 reused

        elif cs.state_type == CompoundStateType.CAMPAIGN_BANISH_BURN:
            # §5.5.7.III: Attacker chooses to burn half favor or skip
            mask[59] = 1.0  # Skip burn (CAMPAIGN_NO_BATTLE reused)
            if cs.banish_target is not None:
                defender = gs.players[cs.banish_target]
                if defender.favor > 0:
                    mask[87] = 1.0  # Burn favor (CAMPAIGN_DONE_TARGETS reused)

        elif cs.state_type == CompoundStateType.CAMPAIGN_PLACE_WARBANDS:
            # §5.5.7.I: Attacker chooses 0 to force_remaining warbands
            # to place on the current targeted site (actions 123–131)
            max_place = min(cs.campaign_force_remaining, 8)
            for i in range(max_place + 1):
                mask[123 + i] = 1.0

        return mask

    def _get_vow_mask(self, gs: GameState, player_index: int) -> np.ndarray:
        """Get legal mask during vow phase — only VOW actions for the winner."""
        mask = np.zeros(NUM_ACTIONS, dtype=np.float32)
        if gs.winner != player_index:
            return mask

        # Vision-locked rule (§8.1): vision winner must vow matching oath
        winner_player = gs.players[gs.winner]
        if winner_player.revealed_vision is not None:
            locked_goal = VISION_TO_OATH_GOAL.get(winner_player.revealed_vision)
            if locked_goal is not None:
                mask[119 + int(locked_goal)] = 1.0
                return mask

        # Otherwise all 4 oath goals are legal
        for goal in OathGoal:
            mask[119 + int(goal)] = 1.0
        return mask
