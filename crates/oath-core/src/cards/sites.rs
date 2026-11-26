use crate::state::*;
use crate::types::*;

/// All 23 Sites (OATH-237..OATH-259):
/// - 237 Ancient City, 241 Deep Woods, 243 Fertile Valley, 256 Standing Stones, 257 Steppe, 259 Wastes:
///   handled in `on_card_played_to_site` (Homeland Search powers).
/// - 238 Barren Coast, 246 Lush Coast, 253 Rocky Coast, 239 Buried Giant, 240 Charming Valley,
///   250 Narrow Pass, 255 Shrouded Wood, 258 The Hidden Place:
///   handled in `travel_cost` / `can_travel` / `execute_travel` / `can_target_site`.
/// - 242 Drowned City, 248 Mine, 254 Salt Flats:
///   handled in `resume_wake_phase` (Wake powers).
/// - 244 Great Slum: handled in `can_play_search_card` / `place_played_card`.
/// - 247 Marshes: handled in `execute_search` (-1 card drawn).
/// - 249 Mountain, 251 Plains: handled in `begin_battle_plans` (-1/+1 attack die).
/// - 252 River: handled in `execute_muster` (+1 warband if ruled).
/// - 245 The Tribunal: Action power handled right here!

pub fn can_use_site_action(gs: &GameState, player: PlayerId, site_id: CardId) -> bool {
    if site_id == SITE_THE_TRIBUNAL {
        let p_site = gs.players[player as usize].pawn_site;
        let at_or_rules = gs.sites[p_site as usize].site_id == SITE_THE_TRIBUNAL
            || (0..MAX_SITES as u8).any(|si| {
                gs.sites[si as usize].is_faceup
                    && gs.sites[si as usize].site_id == SITE_THE_TRIBUNAL
                    && gs.player_rules_site(player, si)
            });
        return at_or_rules && gs.num_players >= 2;
    }
    false
}

pub fn execute_site_action(gs: &mut GameState, player: PlayerId, site_id: CardId) {
    if site_id == SITE_THE_TRIBUNAL {
        let mut allowed = 0u8;
        for p in 0..gs.num_players {
            if p != player {
                allowed |= 1u8 << p;
            }
        }
        gs.effect_stack.push(PendingEffect::ResumeCardEffect {
            card_id: SITE_THE_TRIBUNAL,
            player,
            step: 0,
            aux: 0,
        });
        gs.decision = DecisionPoint::ChoosePlayer {
            player,
            reason: ChoiceReason::DealPartner,
            allowed_mask: allowed,
        };
    }
}
