use crate::cards::get_card;
use crate::engine::major_actions::execute_travel;
use crate::engine::win::recalculate_oathkeeper;
use crate::state::*;
use crate::types::*;

/// All 21 Relics (OATH-211..OATH-231):
/// Passive/modifier/battle-plan relics are hooked directly in engine modules:
/// - 211 Sticky Fire, 212 Cursed Cauldron, 228 Obsidian Cage (Battle Plan): campaign.rs
/// - 214 Truthful Harp, 220 Cracked Horn, 229 Book of Records (Search): major_actions.rs
/// - 215 Grand Mask, 221 Bandit Crown (Rule): state.rs
/// - 217 Cup of Plenty (Trade): major_actions.rs
/// - 222 Ring of Devotion (Muster/Warbands): major_actions.rs, minor_actions.rs, campaign.rs
/// - 225 Circlet of Command (Protection): major_actions.rs, campaign.rs
/// - 230 Dragonskin Drum (Travel): major_actions.rs
/// - 231 The Grand Scepter (Peek/Citizenship/Exile): minor_actions.rs
///
/// Active `Action:` relics are handled right here:
/// - 213 Brass Horse, 216 Horned Mask, 218 Whistle, 219 Dowsing Sticks,
/// - 223 Skeleton Key, 224 Oracular Pig, 226 Ivory Eye, 227 Map, 228 Obsidian Cage (release).

pub fn can_use_relic_action(gs: &GameState, player: PlayerId, relic_id: CardId) -> bool {
    let p = &gs.players[player as usize];
    match relic_id {
        RELIC_BRASS_HORSE => true,
        RELIC_HORNED_MASK => {
            let has_faceup_adv = (0..MAX_ADVISERS)
                .any(|sl| p.advisers[sl] != CARD_EMPTY && p.adviser_faceup[sl]);
            let site = &gs.sites[p.pawn_site as usize];
            let has_site_card = site.is_faceup && site.num_cards() > 0;
            has_faceup_adv && has_site_card
        }
        RELIC_WHISTLE => {
            p.secrets_faceup > 0
                && (0..gs.num_players)
                    .any(|o| o != player && gs.players[o as usize].pawn_site != p.pawn_site)
        }
        RELIC_DOWSING_STICKS => !gs.relic_deck.is_empty(),
        RELIC_SKELETON_KEY => {
            let chanc = gs.chancellor_index();
            gs.player_rules_site(chanc, p.pawn_site) && !gs.reliquary.is_empty()
        }
        RELIC_ORACULAR_PIG => !gs.world_deck.is_empty(),
        RELIC_IVORY_EYE => {
            // Can peek at any facedown site, adviser, or site relic not yet known
            (0..MAX_SITES).any(|si| !gs.sites[si].is_faceup)
                || (0..gs.num_players).any(|o| {
                    o != player
                        && (0..MAX_ADVISERS).any(|sl| {
                            gs.players[o as usize].advisers[sl] != CARD_EMPTY
                                && !gs.players[o as usize].adviser_faceup[sl]
                                && !gs.knowledge[player as usize].knows_adviser(o, sl)
                        })
                })
        }
        RELIC_MAP => true,
        RELIC_OBSIDIAN_CAGE => gs.obsidian_cage_warbands.iter().any(|&w| w > 0),
        _ => false,
    }
}

pub fn execute_relic_action(gs: &mut GameState, player: PlayerId, relic_id: CardId) {
    match relic_id {
        // OATH-213 Brass Horse: reveal top of region discard pile; travel free to site with card of that suit (or any site)
        RELIC_BRASS_HORSE => {
            let cur_site = gs.players[player as usize].pawn_site;
            let region = gs.sites[cur_site as usize].region;
            let top_suit = gs.discard_piles[region as usize]
                .last()
                .and_then(|&cid| get_card(cid).suit);
            let mut matching_mask = 0u8;
            if let Some(suit) = top_suit {
                for si in 0..MAX_SITES as u8 {
                    if si != cur_site && gs.sites[si as usize].is_faceup {
                        if gs.sites[si as usize].cards[..gs.sites[si as usize].capacity as usize]
                            .iter()
                            .any(|&c| c != CARD_EMPTY && get_card(c).suit == Some(suit))
                        {
                            matching_mask |= 1u8 << si;
                        }
                    }
                }
            }
            if matching_mask == 0 {
                for si in 0..MAX_SITES as u8 {
                    if si != cur_site {
                        matching_mask |= 1u8 << si;
                    }
                }
            }
            gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                card_id: RELIC_BRASS_HORSE,
                player,
                step: 0,
                aux: 0,
            });
            gs.decision = DecisionPoint::ChooseSite {
                player,
                reason: ChoiceReason::CardTargetSite,
                allowed_mask: matching_mask,
            };
        }

        // OATH-216 Horned Mask: swap one faceup adviser with a card at your site
        RELIC_HORNED_MASK => {
            let p_site = gs.players[player as usize].pawn_site;
            let adv_slot = (0..MAX_ADVISERS).find(|&sl| {
                gs.players[player as usize].advisers[sl] != CARD_EMPTY
                    && gs.players[player as usize].adviser_faceup[sl]
                    && get_card(gs.players[player as usize].advisers[sl]).restriction
                        != CardRestriction::Locked
            });
            let site_slot = (0..gs.sites[p_site as usize].capacity as usize).find(|&sl| {
                let c = gs.sites[p_site as usize].cards[sl];
                c != CARD_EMPTY && get_card(c).restriction != CardRestriction::Locked
            });
            if let (Some(aslot), Some(sslot)) = (adv_slot, site_slot) {
                let adv_c = gs.players[player as usize].advisers[aslot];
                let site_c = gs.sites[p_site as usize].cards[sslot];
                gs.players[player as usize].advisers[aslot] = site_c;
                gs.sites[p_site as usize].cards[sslot] = adv_c;
            }
        }

        // OATH-218 Whistle: choose a pawn at another site; they travel free to your site and receive 1 secret
        RELIC_WHISTLE => {
            let p_site = gs.players[player as usize].pawn_site;
            let mut allowed = 0u8;
            for o in 0..gs.num_players {
                if o != player && gs.players[o as usize].pawn_site != p_site {
                    allowed |= 1u8 << o;
                }
            }
            if allowed != 0 {
                gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                    card_id: RELIC_WHISTLE,
                    player,
                    step: 0,
                    aux: 0,
                });
                gs.decision = DecisionPoint::ChoosePlayer {
                    player,
                    reason: ChoiceReason::CardTargetPlayer,
                    allowed_mask: allowed,
                };
            }
        }

        // OATH-219 Dowsing Sticks: draw a relic; choose to keep or put on bottom of relic deck
        RELIC_DOWSING_STICKS => {
            if let Some(rid) = gs.relic_deck.pop() {
                gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                    card_id: RELIC_DOWSING_STICKS,
                    player,
                    step: 0,
                    aux: rid,
                });
                gs.decision = DecisionPoint::ChooseYesNo {
                    player,
                    reason: ChoiceReason::DowsingSticksKeep,
                    source_card: RELIC_DOWSING_STICKS,
                };
            }
        }

        // OATH-223 Skeleton Key: peek at Reliquary and take 1 relic
        RELIC_SKELETON_KEY => {
            if let Some(rid) = gs.reliquary.pop() {
                gs.players[player as usize].relics.push(rid);
                recalculate_oathkeeper(gs);
            }
        }

        // OATH-224 Oracular Pig: peek at top 3 cards of world deck -> updates KnowledgeState
        RELIC_ORACULAR_PIG => {
            gs.knowledge[player as usize].known_world_deck_top.clear();
            let len = gs.world_deck.len();
            for i in 0..3.min(len) {
                gs.knowledge[player as usize]
                    .known_world_deck_top
                    .push(gs.world_deck[len - 1 - i]);
            }
        }

        // OATH-226 Ivory Eye: peek at any facedown site, opponent adviser, or site relic -> updates KnowledgeState
        RELIC_IVORY_EYE => {
            // Mark first unknown facedown site, or unknown adviser, or unknown site relic as known
            for si in 0..MAX_SITES {
                if !gs.sites[si].is_faceup
                    && (gs.knowledge[player as usize].known_facedown_sites_mask & (1u8 << si)) == 0
                {
                    gs.knowledge[player as usize].known_facedown_sites_mask |= 1u8 << si;
                    return;
                }
            }
            for o in 0..gs.num_players {
                if o == player {
                    continue;
                }
                for sl in 0..MAX_ADVISERS {
                    if gs.players[o as usize].advisers[sl] != CARD_EMPTY
                        && !gs.players[o as usize].adviser_faceup[sl]
                        && !gs.knowledge[player as usize].knows_adviser(o, sl)
                    {
                        gs.knowledge[player as usize].mark_adviser_known(o, sl);
                        return;
                    }
                }
            }
        }

        // OATH-227 Map: put Map on bottom of relic deck to gain 4 Supply
        RELIC_MAP => {
            if let Some(pos) = gs.players[player as usize]
                .relics
                .iter()
                .position(|&r| r == RELIC_MAP)
            {
                gs.players[player as usize].relics.remove(pos);
                gs.relic_deck.insert(0, RELIC_MAP);
                gs.players[player as usize].supply =
                    (gs.players[player as usize].supply + 4).min(MAX_SUPPLY);
                recalculate_oathkeeper(gs);
            }
        }

        // OATH-228 Obsidian Cage: release caged warbands back to boards of matching color
        RELIC_OBSIDIAN_CAGE => {
            for p in 0..gs.num_players as usize {
                let wb = gs.obsidian_cage_warbands[p];
                if wb > 0 {
                    gs.obsidian_cage_warbands[p] = 0;
                    gs.players[p].warbands_board += wb;
                }
            }
        }

        _ => {}
    }
}

pub fn resume_relic_site_choice(gs: &mut GameState, player: PlayerId, relic_id: CardId, site: SiteIndex) {
    if relic_id == RELIC_BRASS_HORSE {
        execute_travel(gs, player, site, true);
    }
    gs.decision = DecisionPoint::TurnAct { player };
}

pub fn resume_relic_player_choice(gs: &mut GameState, player: PlayerId, relic_id: CardId, target: PlayerId) {
    if relic_id == RELIC_WHISTLE {
        let dest = gs.players[player as usize].pawn_site;
        execute_travel(gs, target, dest, true);
        if gs.players[player as usize].secrets_faceup > 0 {
            gs.players[player as usize].secrets_faceup -= 1;
            gs.players[target as usize].secrets_faceup += 1;
        }
    }
    gs.decision = DecisionPoint::TurnAct { player };
}
