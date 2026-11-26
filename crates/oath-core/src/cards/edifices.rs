use crate::cards::get_card;
use crate::state::*;
use crate::types::*;

/// All 12 Edifices (OATH-199..OATH-210):
/// - 199 Sprawling Rampart: +1 defense die per ruled site targeted (campaign.rs)
/// - 200 Bandit Rampart: -2 attack dice if site targeted (campaign.rs)
/// - 201 Hall of Debate: players cannot target People's Favor (campaign.rs)
/// - 202 Hall of Mockery: recovering PF always flips to Mob (major_actions.rs)
/// - 203 Forest Temple: Chronicle keep Beast sites (chronicle.rs)
/// - 204 Ruined Temple: enemies cannot play Beast faceup (major_actions.rs)
/// - 205 Festival District: Action: binding exchange of favor, secrets, advisers (here!)
/// - 206 Squalid District: +/-1 end die roll (turn.rs)
/// - 207 Great Spire: Search swap with Dispossessed (major_actions.rs)
/// - 208 Fallen Spire: Action: swap up to 5 region discards with Dispossessed (here!)
/// - 209 Ancient Forge: Action: draw a relic, keep or put on bottom (here!)
/// - 210 Broken Forge: Action: flip this card over to Ancient Forge (here!)

pub fn can_use_edifice_action(gs: &GameState, _player: PlayerId, edifice_id: CardId) -> bool {
    match edifice_id {
        EDIFICE_FESTIVAL_DISTRICT => gs.num_players >= 2,
        EDIFICE_FALLEN_SPIRE => !gs.dispossessed.is_empty(),
        EDIFICE_ANCIENT_FORGE => !gs.relic_deck.is_empty(),
        EDIFICE_BROKEN_FORGE => true,
        _ => false,
    }
}

pub fn execute_edifice_action(gs: &mut GameState, player: PlayerId, edifice_id: CardId) {
    match edifice_id {
        EDIFICE_FESTIVAL_DISTRICT => {
            let mut allowed = 0u8;
            for p in 0..gs.num_players {
                if p != player {
                    allowed |= 1u8 << p;
                }
            }
            gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                card_id: EDIFICE_FESTIVAL_DISTRICT,
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

        EDIFICE_FALLEN_SPIRE => {
            let site_idx = gs.players[player as usize].pawn_site;
            let region = gs.sites[site_idx as usize].region as usize;
            let mut swapped = 0;
            for i in (0..gs.discard_piles[region].len()).rev() {
                if swapped >= 5 || gs.dispossessed.is_empty() {
                    break;
                }
                let cid = gs.discard_piles[region][i];
                if get_card(cid).card_type == CardType::Denizen {
                    let di = gs.rng.gen_range_usize(gs.dispossessed.len());
                    let replacement = gs.dispossessed.swap_remove(di);
                    gs.discard_piles[region][i] = replacement;
                    gs.dispossessed.push(cid);
                    swapped += 1;
                }
            }
        }

        EDIFICE_ANCIENT_FORGE => {
            if let Some(rid) = gs.relic_deck.pop() {
                gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                    card_id: EDIFICE_ANCIENT_FORGE,
                    player,
                    step: 0,
                    aux: rid,
                });
                gs.decision = DecisionPoint::ChooseYesNo {
                    player,
                    reason: ChoiceReason::DowsingSticksKeep,
                    source_card: EDIFICE_ANCIENT_FORGE,
                };
            }
        }

        EDIFICE_BROKEN_FORGE => {
            for si in 0..MAX_SITES {
                for sl in 0..MAX_CARDS_PER_SITE {
                    if gs.sites[si].cards[sl] == EDIFICE_BROKEN_FORGE {
                        gs.sites[si].cards[sl] = EDIFICE_ANCIENT_FORGE;
                        return;
                    }
                }
            }
        }

        _ => {}
    }
}
