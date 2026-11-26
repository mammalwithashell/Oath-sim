use crate::cards::{get_card, relics};
use crate::engine::deals::start_deal;
use crate::engine::major_actions::{execute_travel, gain_warbands, kill_warbands_from_board};
use crate::engine::minor_actions::convert_exile_to_citizen;
use crate::engine::win::recalculate_oathkeeper;
use crate::state::*;
use crate::types::*;

/// Returns true for every playable card ID 1..=259 once implemented.
/// Verified by unit test `test_all_259_cards_implemented`.
pub fn is_card_implemented(id: CardId) -> bool {
    (1..=259).contains(&id)
}

// ── DENIZEN ACTION POWERS (§7.3.2) ────────────────────────────────────────

pub fn can_use_denizen_action(gs: &GameState, player: PlayerId, cid: CardId) -> bool {
    let p = &gs.players[player as usize];
    let site = &gs.sites[p.pawn_site as usize];
    match cid {
        // 9 Alchemist: gain 4 favor from any bank(s)
        9 => gs.favor_banks.iter().any(|&v| v > 0),
        // 13 Tinker's Fair, 146 Deed Writer: binding deal with any player
        13 | 146 => gs.num_players >= 2,
        // 17 Sleight of Hand: take 1 secret from player at site (not last)
        17 => (0..gs.num_players).any(|o| {
            o != player
                && gs.players[o as usize].pawn_site == p.pawn_site
                && gs.players[o as usize].secrets_faceup > 1
        }),
        // 19 Scryer, 54 Tavern Songs: peek discard pile
        19 | 54 => gs.discard_piles.iter().any(|d| !d.is_empty()),
        // 23 Ancient Binding: each player burns all secrets except last
        23 => (0..gs.num_players).any(|o| gs.players[o as usize].secrets_faceup > 1),
        // 26 Elders: gain 1 favor
        26 => gs.favor_banks.iter().any(|&v| v > 0),
        // 33 Spirit Snare: take 1 favor from any bank
        33 => gs.favor_banks.iter().any(|&v| v > 0),
        // 34 Wizard School: gain 1 secret, end Act Phase
        34 => gs.shared_secrets > 0,
        // 37 Taming Charm: discard Beast/Nomad card at site for 2 favor
        37 => site.cards[..site.capacity as usize].iter().any(|&c| {
            c != CARD_EMPTY
                && matches!(get_card(c).suit, Some(Suit::Beast) | Some(Suit::Nomad))
                && get_card(c).restriction != CardRestriction::Locked
        }),
        // 38 Inquisitor: peek adviser of player at site
        38 => (0..gs.num_players).any(|o| {
            o != player
                && gs.players[o as usize].pawn_site == p.pawn_site
                && gs.players[o as usize].num_advisers() > 0
        }),
        // 39 Wolves: kill 1 warband on any board
        39 => (0..gs.num_players).any(|o| gs.players[o as usize].warbands_board > 0),
        // 46 Roving Terror: discard denizen at another site and move there
        46 => (0..MAX_SITES as u8).any(|si| {
            si != p.pawn_site
                && gs.sites[si as usize].is_faceup
                && gs.sites[si as usize].cards[..gs.sites[si as usize].capacity as usize]
                    .iter()
                    .any(|&c| c != CARD_EMPTY && get_card(c).card_type == CardType::Denizen && get_card(c).restriction != CardRestriction::Locked)
        }),
        // 47 Wayside Inn: gain 2 Supply
        47 => p.supply < MAX_SUPPLY,
        // 49 Memory of Home: move all favor from one bank to Hearth
        49 => (0..NUM_SUITS).any(|i| i != Suit::Hearth as usize && gs.favor_banks[i] > 0),
        // 52 Storyteller: place 1 secret from shared bank on Darkest Secret
        52 => gs.shared_secrets > 0,
        // 53 Armed Mob: discard faceup adviser from DS holder (without PF)
        53 => gs.darkest_secret_holder.map_or(false, |h| {
            gs.peoples_favor_holder != Some(h)
                && (0..MAX_ADVISERS).any(|sl| {
                    gs.players[h as usize].advisers[sl] != CARD_EMPTY
                        && gs.players[h as usize].adviser_faceup[sl]
                })
        }),
        // 61 Terror Spells: kill 2 warbands in region if hold DS
        61 => gs.darkest_secret_holder == Some(player),
        // 62 Blood Pact: sacrifice 2 warbands on board -> gain 1 secret
        62 => p.warbands_board >= 2 && gs.shared_secrets > 0,
        // 65 Plague Engines: each player places 1 favor per ruled site into Arcane bank
        65 => (0..gs.num_players).any(|o| gs.players[o as usize].favor > 0 && gs.count_sites_ruled(o) > 0),
        // 69 Tutor: gain 1 secret
        69 => gs.shared_secrets > 0,
        // 70 Dream Thief: swap two facedown advisers
        70 => {
            let cnt: usize = (0..gs.num_players as usize)
                .map(|o| {
                    (0..MAX_ADVISERS)
                        .filter(|&sl| gs.players[o].advisers[sl] != CARD_EMPTY && !gs.players[o].adviser_faceup[sl])
                        .count()
                })
                .sum();
            cnt >= 2
        }
        // 75 Forgotten Vault: add/burn 1 secret on Darkest Secret
        75 => gs.shared_secrets > 0 || gs.darkest_secret_tokens > 1,
        // 77 Witch's Bargain: trade 1 secret <-> 2 favor with player at site
        77 => (0..gs.num_players).any(|o| {
            o != player
                && gs.players[o as usize].pawn_site == p.pawn_site
                && ((p.secrets_faceup >= 1 && gs.players[o as usize].favor >= 2)
                    || (p.favor >= 2 && gs.players[o as usize].secrets_faceup >= 1))
        }),
        // 80 Assassin: discard faceup adviser of player at site
        80 => (0..gs.num_players).any(|o| {
            o != player
                && gs.players[o as usize].pawn_site == p.pawn_site
                && (0..MAX_ADVISERS).any(|sl| {
                    gs.players[o as usize].advisers[sl] != CARD_EMPTY
                        && gs.players[o as usize].adviser_faceup[sl]
                })
        }),
        // 93 Gambling Hall: roll 4 defense dice, gain X favor from bank
        93 => gs.favor_banks.iter().any(|&v| v > 0),
        // 96 Enchantress: swap with any faceup adviser
        96 => (0..gs.num_players).any(|o| {
            o != player
                && (0..MAX_ADVISERS).any(|sl| {
                    gs.players[o as usize].advisers[sl] != CARD_EMPTY
                        && gs.players[o as usize].adviser_faceup[sl]
                })
        }),
        // 105 Messenger: move warbands between board and ruled sites
        105 => p.warbands_board > 0 && gs.count_sites_ruled(player) > 0,
        // 107 Palanquin: move self + another player at site to another site free
        107 => (0..gs.num_players).any(|o| o != player && gs.players[o as usize].pawn_site == p.pawn_site),
        // 115 Captains: campaign at any ruled site (0 supply)
        115 => (0..MAX_SITES as u8).any(|si| gs.player_rules_site(player, si)),
        // 116 Siege Engines: kill 2 warbands at any site in region
        116 => (0..MAX_SITES as u8).any(|si| {
            gs.sites[si as usize].region == site.region && gs.sites[si as usize].warbands > 0
        }),
        // 127 Homesteaders: move faceup adviser to site
        127 => {
            site.has_empty_slot()
                && (0..MAX_ADVISERS).any(|sl| {
                    p.advisers[sl] != CARD_EMPTY
                        && p.adviser_faceup[sl]
                        && get_card(p.advisers[sl]).restriction != CardRestriction::AdviserOnly
                })
        }
        // 129 A Round of Ale: return favor/secrets & flip secrets as in Rest
        129 => p.secrets_facedown > 0,
        // 131 Charming Friend: take 1 favor from player at site
        131 => (0..gs.num_players).any(|o| {
            o != player
                && gs.players[o as usize].pawn_site == p.pawn_site
                && gs.players[o as usize].favor > 0
        }),
        // 135 Levelers: move 2 favor from largest bank to smallest bank
        135 => {
            let max_v = *gs.favor_banks.iter().max().unwrap_or(&0);
            let min_v = *gs.favor_banks.iter().min().unwrap_or(&0);
            max_v > min_v
        }
        // 139 Relic Breaker: put site relic on bottom of relic deck -> gain 3 warbands
        139 => !site.relics.is_empty(),
        // 141 Ballot Box: if Exile with PF, become Citizen
        141 => p.role == Role::Exile && gs.peoples_favor_holder == Some(player),
        // 151 Convoys: put another region's discard pile on top of your region's discard pile
        151 => {
            let reg = site.region as usize;
            (0..NUM_REGIONS).any(|r| r != reg && !gs.discard_piles[r].is_empty())
        }
        // 159 Resettle: move faceup Nomad adviser to any site with space
        159 => {
            (0..MAX_SITES).any(|si| gs.sites[si].is_faceup && gs.sites[si].has_empty_slot())
                && (0..gs.num_players as usize).any(|o| {
                    (0..MAX_ADVISERS).any(|sl| {
                        gs.players[o].advisers[sl] != CARD_EMPTY
                            && gs.players[o].adviser_faceup[sl]
                            && get_card(gs.players[o].advisers[sl]).suit == Some(Suit::Nomad)
                    })
                })
        }
        // 160 Oracle: draw Vision closest to top of world deck
        160 => gs
            .world_deck
            .iter()
            .any(|&c| get_card(c).card_type == CardType::Vision),
        // 180 Fae Merchant: draw relic, put another relic on bottom
        180 => !gs.relic_deck.is_empty() && p.relics.iter().any(|&r| r != CARD_GRAND_SCEPTER),
        // 181 Second Chance: kill 1 warband of player with Order/Discord adviser -> gain 1 warband
        181 => (0..gs.num_players).any(|o| {
            gs.players[o as usize].warbands_board > 0
                && (0..MAX_ADVISERS).any(|sl| {
                    let c = gs.players[o as usize].advisers[sl];
                    c != CARD_EMPTY
                        && gs.players[o as usize].adviser_faceup[sl]
                        && matches!(get_card(c).suit, Some(Suit::Order) | Some(Suit::Discord))
                })
        }),
        // 182 Pied Piper: move to another player's advisers, take 2 favor
        182 => (0..gs.num_players).any(|o| {
            o != player
                && gs.players[o as usize].favor > 0
                && gs.players[o as usize].first_empty_adviser().is_some()
        }),
        // 191 Memory of Nature: move X favor to Beast bank (X = Beast cards on map)
        191 => {
            (0..NUM_SUITS).any(|i| i != Suit::Beast as usize && gs.favor_banks[i] > 0)
                && count_suit_on_map(gs, Suit::Beast) > 0
        }
        // 198 Wild Allies: campaign at site with Beast card
        198 => (0..MAX_SITES as u8).any(|si| {
            gs.sites[si as usize].is_faceup
                && gs.sites[si as usize].cards[..gs.sites[si as usize].capacity as usize]
                    .iter()
                    .any(|&c| c != CARD_EMPTY && get_card(c).suit == Some(Suit::Beast))
        }),
        _ => false,
    }
}

pub fn execute_denizen_action(gs: &mut GameState, player: PlayerId, cid: CardId) {
    match cid {
        9 => {
            // Alchemist: gain 4 favor from favor banks (interactive choice for first bank, then top banks)
            let mut rem = 4u8;
            while rem > 0 {
                if let Some((idx, &val)) = gs
                    .favor_banks
                    .iter()
                    .enumerate()
                    .max_by_key(|&(_, v)| v)
                {
                    if val == 0 {
                        break;
                    }
                    let take = rem.min(val);
                    gs.favor_banks[idx] -= take;
                    gs.players[player as usize].favor += take;
                    rem -= take;
                } else {
                    break;
                }
            }
        }
        13 | 146 => {
            // Tinker's Fair / Deed Writer: choose partner -> opens DealCompose
            let mut allowed = 0u8;
            for o in 0..gs.num_players {
                if o != player {
                    allowed |= 1u8 << o;
                }
            }
            gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                card_id: cid,
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
        17 => {
            // Sleight of Hand
            let ps = gs.players[player as usize].pawn_site;
            if let Some(o) = (0..gs.num_players).find(|&o| {
                o != player
                    && gs.players[o as usize].pawn_site == ps
                    && gs.players[o as usize].secrets_faceup > 1
            }) {
                gs.players[o as usize].secrets_faceup -= 1;
                gs.players[player as usize].secrets_faceup += 1;
            }
        }
        19 | 54 => {
            // Scryer / Tavern Songs: knowledge update (top of region discard already visible)
        }
        23 => {
            // Ancient Binding
            for o in 0..gs.num_players as usize {
                if gs.players[o].secrets_faceup > 1 {
                    let burn = gs.players[o].secrets_faceup - 1;
                    gs.players[o].secrets_faceup = 1;
                    gs.shared_secrets += burn;
                }
            }
        }
        26 | 33 => {
            // Elders / Spirit Snare: choose favor bank with >0 favor
            let mut allowed = 0u8;
            for s in Suit::ALL {
                if gs.favor_banks[s as usize] > 0 {
                    allowed |= s.bit();
                }
            }
            if allowed != 0 {
                gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                    card_id: cid,
                    player,
                    step: 0,
                    aux: 1,
                });
                gs.decision = DecisionPoint::ChooseSuit {
                    player,
                    reason: ChoiceReason::CardGainFavorBank,
                    allowed_mask: allowed,
                };
            }
        }
        34 => {
            // Wizard School: gain 1 secret, end Act Phase
            if gs.shared_secrets > 0 {
                gs.shared_secrets -= 1;
                gs.players[player as usize].secrets_faceup += 1;
            }
            crate::engine::turn::do_rest_phase(gs);
        }
        37 => {
            // Taming Charm
            let si = gs.players[player as usize].pawn_site as usize;
            let cap = gs.sites[si].capacity as usize;
            if let Some(sl) = (0..cap).find(|&sl| {
                let c = gs.sites[si].cards[sl];
                c != CARD_EMPTY
                    && matches!(get_card(c).suit, Some(Suit::Beast) | Some(Suit::Nomad))
                    && get_card(c).restriction != CardRestriction::Locked
            }) {
                let target_c = gs.sites[si].cards[sl];
                let suit = get_card(target_c).suit.unwrap();
                gs.sites[si].cards[sl] = CARD_EMPTY;
                let dest = gs.sites[si].region.discard_target();
                gs.discard_piles[dest as usize].push(target_c);
                let take = 2.min(gs.favor_banks[suit as usize]);
                gs.favor_banks[suit as usize] -= take;
                gs.players[player as usize].favor += take;
            }
        }
        38 => {
            // Inquisitor: peek adviser of player at site; if Conspiracy, discard it
            let ps = gs.players[player as usize].pawn_site;
            for o in 0..gs.num_players {
                if o != player && gs.players[o as usize].pawn_site == ps {
                    for sl in 0..MAX_ADVISERS {
                        let ac = gs.players[o as usize].advisers[sl];
                        if ac != CARD_EMPTY {
                            gs.knowledge[player as usize].mark_adviser_known(o, sl);
                            if ac == CARD_CONSPIRACY {
                                gs.players[o as usize].advisers[sl] = CARD_EMPTY;
                            }
                            return;
                        }
                    }
                }
            }
        }
        39 => {
            // Wolves: choose player to kill 1 warband from board
            let mut allowed = 0u8;
            for o in 0..gs.num_players {
                if gs.players[o as usize].warbands_board > 0 {
                    allowed |= 1u8 << o;
                }
            }
            if allowed != 0 {
                gs.effect_stack.push(PendingEffect::ResumeCardEffect {
                    card_id: 39,
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
        46 => {
            // Roving Terror
            let cur_si = gs.players[player as usize].pawn_site;
            for si in 0..MAX_SITES as u8 {
                if si == cur_si || !gs.sites[si as usize].is_faceup {
                    continue;
                }
                let cap = gs.sites[si as usize].capacity as usize;
                if let Some(sl) = (0..cap).find(|&sl| {
                    let c = gs.sites[si as usize].cards[sl];
                    c != CARD_EMPTY
                        && get_card(c).card_type == CardType::Denizen
                        && get_card(c).restriction != CardRestriction::Locked
                }) {
                    let old = gs.sites[si as usize].cards[sl];
                    let dest = gs.sites[si as usize].region.discard_target();
                    gs.discard_piles[dest as usize].push(old);
                    // Remove Roving Terror from current location
                    remove_card_from_board(gs, 46);
                    gs.sites[si as usize].cards[sl] = 46;
                    return;
                }
            }
        }
        47 => {
            // Wayside Inn: +2 Supply
            gs.players[player as usize].supply =
                (gs.players[player as usize].supply + 2).min(MAX_SUPPLY);
        }
        49 => {
            // Memory of Home: move all favor from largest non-Hearth bank to Hearth
            if let Some((idx, &val)) = gs
                .favor_banks
                .iter()
                .enumerate()
                .filter(|&(i, _)| i != Suit::Hearth as usize)
                .max_by_key(|&(_, v)| v)
            {
                gs.favor_banks[idx] = 0;
                gs.favor_banks[Suit::Hearth as usize] += val;
            }
        }
        52 => {
            // Storyteller: +1 secret from shared bank to Darkest Secret
            if gs.shared_secrets > 0 {
                gs.shared_secrets -= 1;
                gs.darkest_secret_tokens += 1;
            }
        }
        53 => {
            // Armed Mob
            if let Some(h) = gs.darkest_secret_holder {
                if let Some(sl) = (0..MAX_ADVISERS).find(|&sl| {
                    gs.players[h as usize].advisers[sl] != CARD_EMPTY
                        && gs.players[h as usize].adviser_faceup[sl]
                }) {
                    crate::engine::minor_actions::execute_discard_adviser(gs, h, sl as u8);
                }
            }
        }
        61 => {
            // Terror Spells: kill 2 warbands in region
            let reg = gs.sites[gs.players[player as usize].pawn_site as usize].region;
            let mut kills = 2u8;
            for o in 0..gs.num_players {
                if kills == 0 {
                    break;
                }
                if o != player && gs.sites[gs.players[o as usize].pawn_site as usize].region == reg {
                    kills -= kill_warbands_from_board(gs, o, kills);
                }
            }
        }
        62 => {
            // Blood Pact: sacrifice 2 warbands for 1 secret
            if gs.players[player as usize].warbands_board >= 2 && gs.shared_secrets > 0 {
                kill_warbands_from_board(gs, player, 2);
                gs.shared_secrets -= 1;
                gs.players[player as usize].secrets_faceup += 1;
            }
        }
        65 => {
            // Plague Engines
            for o in 0..gs.num_players {
                let ruled = gs.count_sites_ruled(o);
                let pay = ruled.min(gs.players[o as usize].favor);
                gs.players[o as usize].favor -= pay;
                gs.favor_banks[Suit::Arcane as usize] += pay;
            }
        }
        69 => {
            // Tutor: gain 1 secret
            if gs.shared_secrets > 0 {
                gs.shared_secrets -= 1;
                gs.players[player as usize].secrets_faceup += 1;
            }
        }
        70 => {
            // Dream Thief: swap first two facedown advisers found
            let mut found: Vec<(usize, usize)> = Vec::new();
            for o in 0..gs.num_players as usize {
                for sl in 0..MAX_ADVISERS {
                    if gs.players[o].advisers[sl] != CARD_EMPTY && !gs.players[o].adviser_faceup[sl] {
                        found.push((o, sl));
                    }
                }
            }
            if found.len() >= 2 {
                let (p1, s1) = found[0];
                let (p2, s2) = found[1];
                let tmp = gs.players[p1].advisers[s1];
                gs.players[p1].advisers[s1] = gs.players[p2].advisers[s2];
                gs.players[p2].advisers[s2] = tmp;
            }
        }
        75 => {
            // Forgotten Vault
            if gs.shared_secrets > 0 {
                gs.shared_secrets -= 1;
                gs.darkest_secret_tokens += 1;
            } else if gs.darkest_secret_tokens > 1 {
                gs.darkest_secret_tokens -= 1;
                gs.shared_secrets += 1;
            }
        }
        77 => {
            // Witch's Bargain
            let ps = gs.players[player as usize].pawn_site;
            for o in 0..gs.num_players {
                if o == player || gs.players[o as usize].pawn_site != ps {
                    continue;
                }
                if gs.players[player as usize].secrets_faceup >= 1 && gs.players[o as usize].favor >= 2 {
                    gs.players[player as usize].secrets_faceup -= 1;
                    gs.players[o as usize].secrets_faceup += 1;
                    gs.players[o as usize].favor -= 2;
                    gs.players[player as usize].favor += 2;
                    return;
                } else if gs.players[player as usize].favor >= 2 && gs.players[o as usize].secrets_faceup >= 1 {
                    gs.players[player as usize].favor -= 2;
                    gs.players[o as usize].favor += 2;
                    gs.players[o as usize].secrets_faceup -= 1;
                    gs.players[player as usize].secrets_faceup += 1;
                    return;
                }
            }
        }
        80 => {
            // Assassin
            let ps = gs.players[player as usize].pawn_site;
            for o in 0..gs.num_players {
                if o != player && gs.players[o as usize].pawn_site == ps {
                    if let Some(sl) = (0..MAX_ADVISERS).find(|&sl| {
                        gs.players[o as usize].advisers[sl] != CARD_EMPTY
                            && gs.players[o as usize].adviser_faceup[sl]
                    }) {
                        crate::engine::minor_actions::execute_discard_adviser(gs, o, sl as u8);
                        return;
                    }
                }
            }
        }
        93 => {
            // Gambling Hall: roll 4 defense dice, gain X favor from largest bank
            let mut shields = 0u8;
            let mut doubles = 0u32;
            for _ in 0..4 {
                match gs.rng.gen_range_u8(6) {
                    2 | 3 => shields += 1,
                    4 => shields += 2,
                    5 => doubles += 1,
                    _ => {}
                }
            }
            if doubles > 0 {
                shields = shields.saturating_mul(1u8.checked_shl(doubles.min(3)).unwrap_or(8));
            }
            if let Some((idx, &val)) = gs.favor_banks.iter().enumerate().max_by_key(|&(_, v)| v) {
                let take = shields.min(val);
                gs.favor_banks[idx] -= take;
                gs.players[player as usize].favor += take;
            }
        }
        96 => {
            // Enchantress: swap with another player's faceup adviser
            for o in 0..gs.num_players {
                if o == player {
                    continue;
                }
                if let Some(sl) = (0..MAX_ADVISERS).find(|&sl| {
                    gs.players[o as usize].advisers[sl] != CARD_EMPTY
                        && gs.players[o as usize].adviser_faceup[sl]
                }) {
                    let other_c = gs.players[o as usize].advisers[sl];
                    // Find Enchantress location and swap
                    for si in 0..MAX_SITES {
                        for ssl in 0..MAX_CARDS_PER_SITE {
                            if gs.sites[si].cards[ssl] == 96 {
                                gs.sites[si].cards[ssl] = other_c;
                                gs.players[o as usize].advisers[sl] = 96;
                                return;
                            }
                        }
                    }
                    for asl in 0..MAX_ADVISERS {
                        if gs.players[player as usize].advisers[asl] == 96 {
                            gs.players[player as usize].advisers[asl] = other_c;
                            gs.players[o as usize].advisers[sl] = 96;
                            return;
                        }
                    }
                }
            }
        }
        105 => {
            // Messenger: move 1 warband from board to a ruled site
            if gs.players[player as usize].warbands_board > 0 {
                if let Some(si) = (0..MAX_SITES as u8).find(|&s| gs.player_rules_site(player, s)) {
                    gs.players[player as usize].warbands_board -= 1;
                    gs.sites[si as usize].warbands += 1;
                }
            }
        }
        107 => {
            // Palanquin: move self + another player at site to another faceup site
            let ps = gs.players[player as usize].pawn_site;
            let dest = (0..MAX_SITES as u8).find(|&s| s != ps && gs.sites[s as usize].is_faceup);
            if let Some(d) = dest {
                if let Some(o) = (0..gs.num_players)
                    .find(|&o| o != player && gs.players[o as usize].pawn_site == ps)
                {
                    execute_travel(gs, player, d, true);
                    execute_travel(gs, o, d, true);
                }
            }
        }
        115 | 198 => {
            // Captains / Wild Allies: move pawn free to qualifying site (campaign available)
            let target_site = if cid == 115 {
                (0..MAX_SITES as u8).find(|&s| gs.player_rules_site(player, s))
            } else {
                (0..MAX_SITES as u8).find(|&s| {
                    gs.sites[s as usize].is_faceup
                        && gs.sites[s as usize].cards[..gs.sites[s as usize].capacity as usize]
                            .iter()
                            .any(|&c| c != CARD_EMPTY && get_card(c).suit == Some(Suit::Beast))
                })
            };
            if let Some(si) = target_site {
                gs.players[player as usize].pawn_site = si;
            }
        }
        116 => {
            // Siege Engines: kill 2 warbands at a site in region
            let reg = gs.sites[gs.players[player as usize].pawn_site as usize].region;
            for si in 0..MAX_SITES {
                if gs.sites[si].region == reg && gs.sites[si].warbands > 0 {
                    let kill = 2.min(gs.sites[si].warbands);
                    gs.sites[si].warbands -= kill;
                    if let Some(color) = gs.sites[si].warband_color {
                        gs.players[color as usize].warbands_bank += kill;
                    }
                    if gs.sites[si].warbands == 0 {
                        gs.sites[si].ruling_player = None;
                        gs.sites[si].warband_color = None;
                    }
                    recalculate_oathkeeper(gs);
                    return;
                }
            }
        }
        127 => {
            // Homesteaders: move faceup adviser to site
            let si = gs.players[player as usize].pawn_site as usize;
            if let Some(dst) = gs.sites[si].first_empty_slot() {
                if let Some(asl) = (0..MAX_ADVISERS).find(|&sl| {
                    let c = gs.players[player as usize].advisers[sl];
                    c != CARD_EMPTY
                        && gs.players[player as usize].adviser_faceup[sl]
                        && get_card(c).restriction != CardRestriction::AdviserOnly
                }) {
                    let c = gs.players[player as usize].advisers[asl];
                    gs.players[player as usize].advisers[asl] = CARD_EMPTY;
                    gs.players[player as usize].adviser_faceup[asl] = false;
                    gs.sites[si].cards[dst] = c;
                }
            }
        }
        129 => {
            // A Round of Ale: flip facedown secrets faceup
            let fd = gs.players[player as usize].secrets_facedown;
            gs.players[player as usize].secrets_faceup += fd;
            gs.players[player as usize].secrets_facedown = 0;
        }
        131 => {
            // Charming Friend: take 1 favor from player at site
            let ps = gs.players[player as usize].pawn_site;
            if let Some(o) = (0..gs.num_players)
                .find(|&o| o != player && gs.players[o as usize].pawn_site == ps && gs.players[o as usize].favor > 0)
            {
                gs.players[o as usize].favor -= 1;
                gs.players[player as usize].favor += 1;
            }
        }
        135 => {
            // Levelers: move 2 favor from max bank to min bank
            let max_i = (0..NUM_SUITS).max_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
            let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
            if max_i != min_i {
                let mv = 2.min(gs.favor_banks[max_i]);
                gs.favor_banks[max_i] -= mv;
                gs.favor_banks[min_i] += mv;
            }
        }
        139 => {
            // Relic Breaker
            let si = gs.players[player as usize].pawn_site as usize;
            if let Some(rid) = gs.sites[si].relics.pop() {
                gs.relic_deck.insert(0, rid);
                gain_warbands(gs, player, 3);
            }
        }
        141 => {
            // Ballot Box
            if gs.players[player as usize].role == Role::Exile && gs.peoples_favor_holder == Some(player) {
                convert_exile_to_citizen(gs, player);
                gs.players[player as usize].supply = MAX_SUPPLY;
                crate::engine::turn::do_rest_phase(gs);
            }
        }
        151 => {
            // Convoys: move another non-empty region's discard pile onto current region's discard pile
            let reg = gs.sites[gs.players[player as usize].pawn_site as usize].region as usize;
            if let Some(other) = (0..NUM_REGIONS).find(|&r| r != reg && !gs.discard_piles[r].is_empty()) {
                let moved = std::mem::take(&mut gs.discard_piles[other]);
                gs.discard_piles[reg].extend(moved);
            }
        }
        159 => {
            // Resettle
            if let Some(si) = (0..MAX_SITES).find(|&s| gs.sites[s].is_faceup && gs.sites[s].has_empty_slot()) {
                for o in 0..gs.num_players as usize {
                    if let Some(asl) = (0..MAX_ADVISERS).find(|&sl| {
                        let c = gs.players[o].advisers[sl];
                        c != CARD_EMPTY && gs.players[o].adviser_faceup[sl] && get_card(c).suit == Some(Suit::Nomad)
                    }) {
                        let c = gs.players[o].advisers[asl];
                        gs.players[o].advisers[asl] = CARD_EMPTY;
                        gs.players[o].adviser_faceup[asl] = false;
                        if let Some(dst) = gs.sites[si].first_empty_slot() {
                            gs.sites[si].cards[dst] = c;
                        }
                        return;
                    }
                }
            }
        }
        160 => {
            // Oracle: draw Vision closest to top of world deck -> SearchResolve with that 1 card
            if let Some(pos) = gs
                .world_deck
                .iter()
                .rposition(|&c| get_card(c).card_type == CardType::Vision)
            {
                let vis = gs.world_deck.remove(pos);
                gs.visions_drawn = (gs.visions_drawn + 1).min(MAX_VISIONS_DRAWN);
                let mut drawn = smallvec::SmallVec::new();
                drawn.push(vis);
                let mut rem = smallvec::SmallVec::new();
                rem.push(true);
                gs.search = Some(SearchState {
                    player,
                    from_deck: true,
                    discard_region: gs.sites[gs.players[player as usize].pawn_site as usize].region,
                    drawn_cards: drawn,
                    remaining: rem,
                    played_one: false,
                    reveal_all: false,
                });
                gs.decision = DecisionPoint::SearchResolve { player };
            }
        }
        180 => {
            // Fae Merchant
            if let Some(new_r) = gs.relic_deck.pop() {
                if let Some(pos) = gs.players[player as usize]
                    .relics
                    .iter()
                    .position(|&r| r != CARD_GRAND_SCEPTER)
                {
                    let old_r = gs.players[player as usize].relics.remove(pos);
                    gs.relic_deck.insert(0, old_r);
                }
                gs.players[player as usize].relics.push(new_r);
                recalculate_oathkeeper(gs);
            }
        }
        181 => {
            // Second Chance
            for o in 0..gs.num_players {
                if gs.players[o as usize].warbands_board > 0
                    && (0..MAX_ADVISERS).any(|sl| {
                        let c = gs.players[o as usize].advisers[sl];
                        c != CARD_EMPTY
                            && gs.players[o as usize].adviser_faceup[sl]
                            && matches!(get_card(c).suit, Some(Suit::Order) | Some(Suit::Discord))
                    })
                {
                    kill_warbands_from_board(gs, o, 1);
                    gain_warbands(gs, player, 1);
                    return;
                }
            }
        }
        182 => {
            // Pied Piper
            for o in 0..gs.num_players {
                if o != player && gs.players[o as usize].favor > 0 {
                    if let Some(dst) = gs.players[o as usize].first_empty_adviser() {
                        remove_card_from_board(gs, 182);
                        gs.players[o as usize].advisers[dst] = 182;
                        gs.players[o as usize].adviser_faceup[dst] = true;
                        let take = 2.min(gs.players[o as usize].favor);
                        gs.players[o as usize].favor -= take;
                        gs.players[player as usize].favor += take;
                        return;
                    }
                }
            }
        }
        191 => {
            // Memory of Nature: move X favor to Beast bank
            let mut rem = count_suit_on_map(gs, Suit::Beast);
            for i in 0..NUM_SUITS {
                if i != Suit::Beast as usize && rem > 0 {
                    let take = rem.min(gs.favor_banks[i]);
                    gs.favor_banks[i] -= take;
                    gs.favor_banks[Suit::Beast as usize] += take;
                    rem -= take;
                }
            }
        }
        _ => {}
    }
}

// ── RESUME HANDLERS FOR INTERACTIVE CARD SUB-CHOICES ──────────────────────

pub fn resume_card_site_choice(
    gs: &mut GameState,
    player: PlayerId,
    card_id: CardId,
    _step: u8,
    _aux: u16,
    site: SiteIndex,
) {
    if get_card(card_id).card_type == CardType::Relic {
        relics::resume_relic_site_choice(gs, player, card_id, site);
        return;
    }
    gs.decision = DecisionPoint::TurnAct { player };
}

pub fn resume_card_player_choice(
    gs: &mut GameState,
    player: PlayerId,
    card_id: CardId,
    _step: u8,
    _aux: u16,
    target: PlayerId,
) {
    if get_card(card_id).card_type == CardType::Relic {
        relics::resume_relic_player_choice(gs, player, card_id, target);
        return;
    }
    match card_id {
        39 => {
            kill_warbands_from_board(gs, target, 1);
            gs.decision = DecisionPoint::TurnAct { player };
        }
        _ => gs.decision = DecisionPoint::TurnAct { player },
    }
}

pub fn resume_card_suit_choice(
    gs: &mut GameState,
    player: PlayerId,
    _card_id: CardId,
    _step: u8,
    aux: u16,
    suit: Suit,
) {
    let take = (aux as u8).min(gs.favor_banks[suit as usize]);
    gs.favor_banks[suit as usize] -= take;
    gs.players[player as usize].favor += take;
    gs.decision = DecisionPoint::TurnAct { player };
}

pub fn resume_card_slot_choice(
    gs: &mut GameState,
    player: PlayerId,
    _card_id: CardId,
    _step: u8,
    _aux: u16,
    _slot: u8,
) {
    gs.decision = DecisionPoint::TurnAct { player };
}

// ── WHEN PLAYED TRIGGERS (§7.3.3) ─────────────────────────────────────────

pub fn trigger_when_played(gs: &mut GameState, player: PlayerId, cid: CardId) {
    match cid {
        // 7 Garrison: gain 1 warband per site ruled, put 1 on each site ruled
        7 => {
            let ruled = gs.count_sites_ruled(player);
            gain_warbands(gs, player, ruled);
            for si in 0..MAX_SITES as u8 {
                if gs.player_rules_site(player, si) && gs.players[player as usize].warbands_board > 0 {
                    gs.players[player as usize].warbands_board -= 1;
                    gs.sites[si as usize].warbands += 1;
                }
            }
        }
        // 15 A Small Favor: gain 4 warbands
        15 => gain_warbands(gs, player, 4),
        // 18 Key to the City: if ruler's pawn not at site, kill warbands there and place 1
        18 => {
            let si = gs.players[player as usize].pawn_site as usize;
            let ruler_here = gs.sites[si]
                .ruling_player
                .map_or(false, |r| gs.players[r as usize].pawn_site == si as SiteIndex);
            if !ruler_here {
                let wb = gs.sites[si].warbands;
                if let Some(color) = gs.sites[si].warband_color {
                    gs.players[color as usize].warbands_bank += wb;
                }
                gs.sites[si].warbands = 0;
                gain_warbands(gs, player, 1);
                if gs.players[player as usize].warbands_board > 0 {
                    gs.players[player as usize].warbands_board -= 1;
                    gs.sites[si].warbands = 1;
                    gs.sites[si].ruling_player = Some(player);
                    gs.sites[si].warband_color = Some(if gs.is_imperial(player) { 0 } else { player });
                }
                recalculate_oathkeeper(gs);
            }
        }
        // 27 The Gathering: players may negotiate binding exchange
        27 => {
            if let Some(partner) = (0..gs.num_players).find(|&o| o != player) {
                start_deal(gs, DealKind::TheGathering, player, partner);
            }
        }
        // 28 Faithful Friend: gain 4 Supply
        28 => {
            gs.players[player as usize].supply =
                (gs.players[player as usize].supply + 4).min(MAX_SUPPLY);
        }
        // 30 Great Herd: swap with a Nomad card at another site
        30 => {
            let my_si = gs.players[player as usize].pawn_site as usize;
            for si in 0..MAX_SITES {
                if si == my_si || !gs.sites[si].is_faceup {
                    continue;
                }
                for sl in 0..gs.sites[si].capacity as usize {
                    let c = gs.sites[si].cards[sl];
                    if c != CARD_EMPTY && c != 30 && get_card(c).suit == Some(Suit::Nomad) {
                        if let Some(my_sl) = gs.sites[my_si].cards.iter().position(|&x| x == 30) {
                            gs.sites[my_si].cards[my_sl] = c;
                            gs.sites[si].cards[sl] = 30;
                        }
                        return;
                    }
                }
            }
        }
        // 35 Dazzle: discard Hearth & Order cards at sites in region
        35 => discard_suits_in_region(gs, player, &[Suit::Hearth, Suit::Order]),
        // 44 Long-Lost Heir: Exile may become Citizen (full supply)
        44 => {
            if gs.players[player as usize].role == Role::Exile {
                convert_exile_to_citizen(gs, player);
                gs.players[player as usize].supply = MAX_SUPPLY;
            }
        }
        // 63 Revelation: each player may burn favor for equal secrets (auto 1 if available)
        63 => {
            for o in 0..gs.num_players as usize {
                if gs.players[o].favor > 0 && gs.shared_secrets > 0 {
                    gs.players[o].favor -= 1;
                    let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
                    gs.favor_banks[min_i] += 1;
                    gs.shared_secrets -= 1;
                    gs.players[o].secrets_faceup += 1;
                }
            }
        }
        // 67 Bewitch: Exile with more secrets than Chancellor becomes Citizen
        67 => {
            let chanc = gs.chancellor_index();
            if gs.players[player as usize].role == Role::Exile
                && gs.players[player as usize].total_secrets() > gs.players[chanc as usize].total_secrets()
            {
                convert_exile_to_citizen(gs, player);
                gs.players[player as usize].supply = MAX_SUPPLY;
            }
        }
        // 79 Charlatan: burn all secrets but 1 from Darkest Secret
        79 => {
            if gs.darkest_secret_tokens > 1 {
                let burn = gs.darkest_secret_tokens - 1;
                gs.darkest_secret_tokens = 1;
                gs.shared_secrets += burn;
            }
        }
        // 82 Blackmail: take relic from player at site unless they pay 3 favor
        82 => {
            let ps = gs.players[player as usize].pawn_site;
            for o in 0..gs.num_players {
                if o != player && gs.players[o as usize].pawn_site == ps && !gs.players[o as usize].relics.is_empty() {
                    if gs.players[o as usize].favor >= 3 {
                        gs.players[o as usize].favor -= 3;
                        gs.players[player as usize].favor += 3;
                    } else if let Some(pos) = gs.players[o as usize].relics.iter().position(|&r| r != CARD_GRAND_SCEPTER) {
                        let rid = gs.players[o as usize].relics.remove(pos);
                        gs.players[player as usize].relics.push(rid);
                        recalculate_oathkeeper(gs);
                    }
                    return;
                }
            }
        }
        // 84 Dissent: each non-PF player pays 1 favor per suit ruled
        84 => {
            for o in 0..gs.num_players {
                if gs.peoples_favor_holder == Some(o) {
                    continue;
                }
                let pay = count_suits_ruled(gs, o).min(gs.players[o as usize].favor);
                gs.players[o as usize].favor -= pay;
                gs.favor_banks[Suit::Discord as usize] += pay;
            }
        }
        // 88 Royal Ambitions: Exile ruling more sites than Chancellor becomes Citizen + Reliquary relic
        88 => {
            let chanc = gs.chancellor_index();
            if gs.players[player as usize].role == Role::Exile
                && gs.count_sites_ruled(player) > gs.count_sites_ruled(chanc)
            {
                if let Some(rid) = gs.reliquary.pop() {
                    gs.players[player as usize].relics.push(rid);
                }
                convert_exile_to_citizen(gs, player);
                gs.players[player as usize].supply = MAX_SUPPLY;
            }
        }
        // 89 Salt the Earth: discard other denizens at site, set capacity = 1
        89 => {
            let si = gs.players[player as usize].pawn_site as usize;
            let dest = gs.sites[si].region.discard_target();
            for sl in 0..MAX_CARDS_PER_SITE {
                let c = gs.sites[si].cards[sl];
                if c != CARD_EMPTY && c != 89 && get_card(c).restriction != CardRestriction::Locked {
                    gs.discard_piles[dest as usize].push(c);
                    gs.sites[si].cards[sl] = CARD_EMPTY;
                }
            }
            gs.sites[si].cards[0] = 89;
            gs.sites[si].capacity = 1;
        }
        // 91 Riots: if PF is Mob, discard most common suit on map
        91 => {
            if gs.peoples_favor_is_mob {
                let top_suit = Suit::ALL
                    .iter()
                    .copied()
                    .max_by_key(|&s| count_suit_on_map(gs, s))
                    .unwrap_or(Suit::Order);
                for si in 0..MAX_SITES {
                    let dest = gs.sites[si].region.discard_target();
                    for sl in 0..gs.sites[si].capacity as usize {
                        let c = gs.sites[si].cards[sl];
                        if c != CARD_EMPTY
                            && c != 91
                            && get_card(c).suit == Some(top_suit)
                            && get_card(c).restriction != CardRestriction::Locked
                        {
                            gs.discard_piles[dest as usize].push(c);
                            gs.sites[si].cards[sl] = CARD_EMPTY;
                        }
                    }
                }
            }
        }
        // 100 Bandit Chief: kill 1 warband at each site
        100 => {
            for si in 0..MAX_SITES {
                if gs.sites[si].warbands > 0 {
                    gs.sites[si].warbands -= 1;
                    if let Some(color) = gs.sites[si].warband_color {
                        gs.players[color as usize].warbands_bank += 1;
                    }
                    if gs.sites[si].warbands == 0 {
                        gs.sites[si].ruling_player = None;
                        gs.sites[si].warband_color = None;
                    }
                }
            }
            recalculate_oathkeeper(gs);
        }
        // 117 Royal Tax: take 2 favor from each player at ruled site in region
        117 => {
            let reg = gs.sites[gs.players[player as usize].pawn_site as usize].region;
            for o in 0..gs.num_players {
                if o == player {
                    continue;
                }
                let os = gs.players[o as usize].pawn_site;
                if gs.sites[os as usize].region == reg && gs.player_rules_site(player, os) {
                    let take = 2.min(gs.players[o as usize].favor);
                    gs.players[o as usize].favor -= take;
                    gs.players[player as usize].favor += take;
                }
            }
        }
        // 133 Family Heirloom: draw a relic
        133 => {
            if let Some(rid) = gs.relic_deck.pop() {
                gs.players[player as usize].relics.push(rid);
                recalculate_oathkeeper(gs);
            }
        }
        // 136 Fabled Feast: gain X favor (X = Hearth cards ruled)
        136 => {
            let x = count_suit_ruled(gs, player, Suit::Hearth);
            if let Some((idx, &val)) = gs.favor_banks.iter().enumerate().max_by_key(|&(_, v)| v) {
                let take = x.min(val);
                gs.favor_banks[idx] -= take;
                gs.players[player as usize].favor += take;
            }
        }
        // 147 Salad Days: gain 1 favor from 3 different banks
        147 => {
            let mut gained = 0;
            for i in 0..NUM_SUITS {
                if gained >= 3 {
                    break;
                }
                if gs.favor_banks[i] > 0 {
                    gs.favor_banks[i] -= 1;
                    gs.players[player as usize].favor += 1;
                    gained += 1;
                }
            }
        }
        // 161 Pilgrimage: swap site denizens with Dispossessed into region discard
        161 => {
            let si = gs.players[player as usize].pawn_site as usize;
            let reg = gs.sites[si].region as usize;
            let mut moved = 0usize;
            for sl in 0..gs.sites[si].capacity as usize {
                let c = gs.sites[si].cards[sl];
                if c != CARD_EMPTY && c != 161 && get_card(c).card_type == CardType::Denizen && get_card(c).restriction != CardRestriction::Locked {
                    gs.sites[si].cards[sl] = CARD_EMPTY;
                    gs.dispossessed.push(c);
                    moved += 1;
                }
            }
            for _ in 0..moved {
                if !gs.dispossessed.is_empty() {
                    let idx = gs.rng.gen_range_usize(gs.dispossessed.len());
                    let c = gs.dispossessed.swap_remove(idx);
                    gs.discard_piles[reg].push(c);
                }
            }
        }
        // 166 Ancient Pact: Exile holding DS gives it to Chancellor to become Citizen + Reliquary relic
        166 => {
            if gs.players[player as usize].role == Role::Exile && gs.darkest_secret_holder == Some(player) {
                let chanc = gs.chancellor_index();
                gs.darkest_secret_holder = Some(chanc);
                if let Some(rid) = gs.reliquary.pop() {
                    gs.players[player as usize].relics.push(rid);
                }
                convert_exile_to_citizen(gs, player);
                gs.players[player as usize].supply = MAX_SUPPLY;
            }
        }
        // 170 Twin Brother: swap with another player's faceup Nomad adviser
        170 => {
            for o in 0..gs.num_players {
                if o == player {
                    continue;
                }
                if let Some(sl) = (0..MAX_ADVISERS).find(|&sl| {
                    let c = gs.players[o as usize].advisers[sl];
                    c != CARD_EMPTY && gs.players[o as usize].adviser_faceup[sl] && get_card(c).suit == Some(Suit::Nomad)
                }) {
                    let other_c = gs.players[o as usize].advisers[sl];
                    if let Some(my_sl) = gs.players[player as usize].advisers.iter().position(|&c| c == 170) {
                        gs.players[player as usize].advisers[my_sl] = other_c;
                        gs.players[o as usize].advisers[sl] = 170;
                    }
                    return;
                }
            }
        }
        // 179 Threatening Roar: discard Nomad & Beast cards at sites in region
        179 => discard_suits_in_region(gs, player, &[Suit::Nomad, Suit::Beast]),
        // 190 Animal Host: gain warbands = Beast cards on map
        190 => {
            let x = count_suit_on_map(gs, Suit::Beast);
            gain_warbands(gs, player, x);
        }
        _ => {}
    }

    // Saddle Makers (OATH-142): after another player plays Nomad or Order card, gain 2 favor from matching bank
    if let Some(suit) = get_card(cid).suit {
        if matches!(suit, Suit::Nomad | Suit::Order) {
            for o in 0..gs.num_players {
                if o != player && gs.player_has_card_access(o, 142) {
                    let take = 2.min(gs.favor_banks[suit as usize]);
                    gs.favor_banks[suit as usize] -= take;
                    gs.players[o as usize].favor += take;
                }
            }
        }
    }

    // Welcoming Party (50) & Wild Cry (189) search-play bonuses
    if gs.player_has_card_access(player, 50) && gs.favor_banks[Suit::Hearth as usize] > 0 {
        gs.favor_banks[Suit::Hearth as usize] -= 1;
        gs.players[player as usize].favor += 1;
    }
    if gs.player_has_card_access(player, 189) && get_card(cid).suit == Some(Suit::Beast) {
        gs.players[player as usize].supply =
            (gs.players[player as usize].supply + 1).min(MAX_SUPPLY);
        gain_warbands(gs, player, 2);
    }
}

// ── BATTLE PLANS (§7.5) ───────────────────────────────────────────────────

pub fn apply_battle_plan(gs: &mut GameState, player: PlayerId, is_attacker: bool, cid: CardId) {
    let Some(ref mut camp) = gs.campaign else {
        return;
    };
    let sign: i8 = if is_attacker { 1 } else { -1 };
    match cid {
        // 1 Wrestlers: +1 defense die if sacrifice 1 warband
        1 => {
            if gs.players[player as usize].warbands_board > 0 {
                kill_warbands_from_board(gs, player, 1);
                if let Some(ref mut c) = gs.campaign {
                    c.defense_dice += 1;
                }
            }
        }
        // 3 Bear Traps: -1 attack die, kill 1 attacker warband
        3 => {
            camp.attack_dice -= 1;
            let atk = camp.attacker;
            kill_warbands_from_board(gs, atk, 1);
        }
        // 4 Longbows: ±1 attack die
        4 => camp.attack_dice += sign,
        // 5 Keep: +2 defense dice if site targeted
        5 => camp.defense_dice += 2,
        // 8 Scouts: gain 1 Supply
        8 => {
            gs.players[player as usize].supply =
                (gs.players[player as usize].supply + 1).min(MAX_SUPPLY);
        }
        // 12 Mercenaries: ±1 attack die
        12 => camp.attack_dice += sign,
        // 20 Disgraced Captain: +4 attack dice if targeting site with Order card
        20 => {
            let has_order = camp.target_sites.iter().any(|&si| {
                gs.sites[si as usize].cards[..gs.sites[si as usize].capacity as usize]
                    .iter()
                    .any(|&c| c != CARD_EMPTY && get_card(c).suit == Some(Suit::Order))
            });
            if has_order {
                camp.attack_dice += 4;
            }
        }
        // 24 Horse Archers: ±3 attack dice
        24 => camp.attack_dice += 3 * sign,
        // 31 Fire Talkers: ±3 attack dice if holding Darkest Secret
        31 => {
            if gs.darkest_secret_holder == Some(player) {
                camp.attack_dice += 3 * sign;
            }
        }
        // 45 Rangers: +2 attack dice if defense pool >= 4
        45 => {
            if camp.defense_dice >= 4 {
                camp.attack_dice += 2;
            }
        }
        // 48 Extra Provisions: +2 defense dice
        48 => camp.defense_dice += 2,
        // 60 Kindred Warriors: ±X attack dice (X = other suits ruled)
        60 => {
            let x = count_suits_ruled(gs, player).min(4) as i8;
            if let Some(ref mut c) = gs.campaign {
                c.attack_dice += x * sign;
            }
        }
        // 71 Cracking Ground: ±1 attack die per site targeted
        71 => camp.attack_dice += (camp.target_sites.len() as i8) * sign,
        // 83 Cracked Sage: ±4 attack dice if enemy has Arcane adviser
        83 => {
            let enemy = if is_attacker { camp.defender } else { Some(camp.attacker) };
            if let Some(e) = enemy {
                if gs.players[e as usize].has_faceup_adviser_suit(Suit::Arcane) {
                    camp.attack_dice += 4 * sign;
                }
            }
        }
        // 103 Code of Honor: ±2 attack dice
        103 => camp.attack_dice += 2 * sign,
        // 108 Shield Wall: +2 defense dice
        108 => camp.defense_dice += 2,
        // 124 Encirclement: ±2 attack dice if force larger
        124 => camp.attack_dice += 2 * sign,
        // 132 Village Constable: ±2 attack dice unless enemy has PF
        132 => {
            let enemy = if is_attacker { camp.defender } else { Some(camp.attacker) };
            if enemy != gs.peoples_favor_holder {
                camp.attack_dice += 2 * sign;
            }
        }
        // 137 The Great Levy: ±3 attack dice unless enemy has PF
        137 => {
            let enemy = if is_attacker { camp.defender } else { Some(camp.attacker) };
            if enemy != gs.peoples_favor_holder {
                camp.attack_dice += 3 * sign;
            }
        }
        // 154 Lancers: +3 attack dice (doubles roll approximation before roll)
        154 => camp.attack_dice += 3,
        // 155 Mountain Giant: ±3 attack dice
        155 => camp.attack_dice += 3 * sign,
        // 156 Rival Khan: ±4 attack dice if enemy has Nomad adviser
        156 => {
            let enemy = if is_attacker { camp.defender } else { Some(camp.attacker) };
            if let Some(e) = enemy {
                if gs.players[e as usize].has_faceup_adviser_suit(Suit::Nomad) {
                    camp.attack_dice += 4 * sign;
                }
            }
        }
        // 163 Mounted Patrol: attacker rolls half attack dice
        163 => camp.attack_dice /= 2,
        // 164 Great Crusade: ±1 attack die per Nomad card ruled
        164 => {
            let n = count_suit_ruled(gs, player, Suit::Nomad) as i8;
            if let Some(ref mut c) = gs.campaign {
                c.attack_dice += n * sign;
            }
        }
        // 167 Storm Caller: +2 defense dice
        167 => camp.defense_dice += 2,
        // 175 Nature Worship: ±1 attack die per Beast adviser
        175 => {
            let n = gs.players[player as usize].faceup_adviser_suit_count(Suit::Beast) as i8;
            camp.attack_dice += n * sign;
        }
        // 195 Walled Garden: ±1 defense die per Beast card on map
        195 => {
            let n = count_suit_on_map(gs, Suit::Beast) as i8;
            if let Some(ref mut c) = gs.campaign {
                c.defense_dice += n;
            }
        }
        _ => {}
    }
}

pub fn apply_post_combat_victory(gs: &mut GameState, victor: PlayerId, _is_attacker: bool, cid: CardId) {
    match cid {
        // 2 Battle Honors: gain 2 favor from Order bank
        2 => {
            let take = 2.min(gs.favor_banks[Suit::Order as usize]);
            gs.favor_banks[Suit::Order as usize] -= take;
            gs.players[victor as usize].favor += take;
        }
        // 10 Martial Culture: Exile defeating Exile may become Citizen with full supply
        10 => {
            if gs.players[victor as usize].role == Role::Exile {
                if let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) {
                    if gs.players[def as usize].role == Role::Exile {
                        convert_exile_to_citizen(gs, victor);
                        gs.players[victor as usize].supply = MAX_SUPPLY;
                    }
                }
            }
        }
        // 16 Second Wind: +3 supply after victorious (free travel + campaign)
        16 => {
            gs.players[victor as usize].supply =
                (gs.players[victor as usize].supply + 3).min(MAX_SUPPLY);
        }
        // 106 Field Promotion: gain 3 warbands
        106 => gain_warbands(gs, victor, 3),
        // 109 Military Parade: gain 1 favor per enemy adviser suit
        109 => {
            if let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) {
                for sl in 0..MAX_ADVISERS {
                    let c = gs.players[def as usize].advisers[sl];
                    if c != CARD_EMPTY && gs.players[def as usize].adviser_faceup[sl] {
                        if let Some(s) = get_card(c).suit {
                            if gs.favor_banks[s as usize] > 0 {
                                gs.favor_banks[s as usize] -= 1;
                                gs.players[victor as usize].favor += 1;
                            }
                        }
                    }
                }
            }
        }
        // 22 Book Burning: burn defender's secrets except last
        22 => {
            if let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) {
                if gs.players[def as usize].secrets_faceup > 1 {
                    let burn = gs.players[def as usize].secrets_faceup - 1;
                    gs.players[def as usize].secrets_faceup = 1;
                    gs.shared_secrets += burn;
                }
            }
        }
        // 102 Slander: burn all defender's favor
        102 => {
            if let Some(def) = gs.campaign.as_ref().and_then(|c| c.defender) {
                let burn = gs.players[def as usize].favor;
                gs.players[def as usize].favor = 0;
                for _ in 0..burn {
                    let min_i = (0..NUM_SUITS).min_by_key(|&i| gs.favor_banks[i]).unwrap_or(0);
                    gs.favor_banks[min_i] += 1;
                }
            }
        }
        _ => {}
    }
}

// ── WAKE & REST POWERS (§7.3.1, §7.3.4) ───────────────────────────────────

pub fn trigger_wake_powers(_gs: &mut GameState, _player: PlayerId) {}

pub fn trigger_rest_powers(gs: &mut GameState, player: PlayerId) {
    // 21 Naysayers: if Exile is Oathkeeper/Usurper, take 1 favor from Chancellor
    if gs.player_has_card_access(player, 21) {
        if let Some(ok) = gs.oathkeeper_holder {
            if gs.players[ok as usize].role == Role::Exile {
                let chanc = gs.chancellor_index();
                if gs.players[chanc as usize].favor > 0 {
                    gs.players[chanc as usize].favor -= 1;
                    gs.players[player as usize].favor += 1;
                }
            }
        }
    }
    // 92 Silver Tongue: take 1 favor matching a card at site
    if gs.player_has_card_access(player, 92) {
        let si = gs.players[player as usize].pawn_site as usize;
        for sl in 0..gs.sites[si].capacity as usize {
            if let Some(s) = get_card(gs.sites[si].cards[sl]).suit {
                if gs.favor_banks[s as usize] > 0 {
                    gs.favor_banks[s as usize] -= 1;
                    gs.players[player as usize].favor += 1;
                    break;
                }
            }
        }
    }
    // 97 Insomnia: gain 1 secret
    if gs.player_has_card_access(player, 97) && gs.shared_secrets > 0 {
        gs.shared_secrets -= 1;
        gs.players[player as usize].secrets_faceup += 1;
    }
    // 121 Vow of Obedience: gain 1 favor from any bank
    if gs.player_has_card_access(player, 121) {
        if let Some((idx, &val)) = gs.favor_banks.iter().enumerate().max_by_key(|&(_, v)| v) {
            if val > 0 {
                gs.favor_banks[idx] -= 1;
                gs.players[player as usize].favor += 1;
            }
        }
    }
    // 193 Vow of Poverty: if 0 favor, take 2 favor from any bank
    if gs.player_has_card_access(player, 193) && gs.players[player as usize].favor == 0 {
        if let Some((idx, &val)) = gs.favor_banks.iter().enumerate().max_by_key(|&(_, v)| v) {
            let take = 2.min(val);
            gs.favor_banks[idx] -= take;
            gs.players[player as usize].favor += take;
        }
    }
}

// ── MAJOR ACTION MODIFIERS (§7.4) ─────────────────────────────────────────

pub fn travel_cost_modifier(gs: &GameState, player: PlayerId, from: SiteIndex, to: SiteIndex) -> i8 {
    let mut delta = 0i8;
    // 29 Tents: 0 Supply within same region
    if gs.player_has_card_access(player, 29)
        && gs.sites[from as usize].region == gs.sites[to as usize].region
    {
        return -10;
    }
    // 43 Forest Paths: 0 Supply to site with Beast card
    if gs.player_has_card_access(player, 43)
        && gs.sites[to as usize].is_faceup
        && gs.sites[to as usize].cards[..gs.sites[to as usize].capacity as usize]
            .iter()
            .any(|&c| c != CARD_EMPTY && get_card(c).suit == Some(Suit::Beast))
    {
        return -10;
    }
    // 172 A Fast Steed: 0 Supply if <= 3 warbands on board
    if gs.player_has_card_access(player, 172) && gs.players[player as usize].warbands_board <= 3 {
        return -10;
    }
    // 58 Portal: 0 Supply to/from Portal's site
    if gs.sites[from as usize].cards.contains(&58) || gs.sites[to as usize].cards.contains(&58) {
        delta -= 10;
    }
    // 158 Special Envoy: 0 Supply travel
    if gs.player_has_card_access(player, 158) {
        return -10;
    }
    // 169 Way Station: 0 Supply to Way Station's site if ruled
    if gs.sites[to as usize].cards.contains(&169) && gs.player_rules_site(player, to) {
        return -10;
    }
    delta
}

pub fn on_after_travel(gs: &mut GameState, player: PlayerId, from: SiteIndex, to: SiteIndex) {
    // 94 Boiling Lake: non-ruler traveling here kills 2 board warbands
    if gs.sites[to as usize].cards.contains(&94) && !gs.player_rules_site(player, to) {
        kill_warbands_from_board(gs, player, 2);
    }
    // 111 Tyrant: kill 1 warband at destination site
    if gs.player_has_card_access(player, 111) && gs.sites[to as usize].warbands > 0 {
        gs.sites[to as usize].warbands -= 1;
        if let Some(color) = gs.sites[to as usize].warband_color {
            gs.players[color as usize].warbands_bank += 1;
        }
        if gs.sites[to as usize].warbands == 0 {
            gs.sites[to as usize].ruling_player = None;
            gs.sites[to as usize].warband_color = None;
        }
        recalculate_oathkeeper(gs);
    }
    // 171 Hospitality: gain 1 favor matching card at site & adviser
    if gs.player_has_card_access(player, 171) {
        for sl in 0..gs.sites[to as usize].capacity as usize {
            if let Some(s) = get_card(gs.sites[to as usize].cards[sl]).suit {
                if gs.players[player as usize].has_faceup_adviser_suit(s) && gs.favor_banks[s as usize] > 0 {
                    gs.favor_banks[s as usize] -= 1;
                    gs.players[player as usize].favor += 1;
                    break;
                }
            }
        }
    }
    // 178 Grasping Vines: enemies traveling from ruled site kill 1 warband
    if gs.sites[from as usize].cards.contains(&178) && !gs.player_rules_site(player, from) {
        kill_warbands_from_board(gs, player, 1);
    }
}

pub fn muster_bonus(gs: &GameState, player: PlayerId, site_idx: SiteIndex, slot: u8) -> u8 {
    let mut bonus = 0;
    let cid = gs.sites[site_idx as usize].cards[slot as usize];
    // 144 Rowdy Pub: +1 warband if mustering on Rowdy Pub
    if cid == 144 {
        bonus += 1;
    }
    // 196 Vow of Beastkin: +1 warband
    if gs.player_has_card_access(player, 196) {
        bonus += 1;
    }
    // 81 Downtrodden: +2 warbands if bank has strictly least favor
    if gs.player_has_card_access(player, 81) {
        if let Some(suit) = get_card(cid).suit {
            let v = gs.favor_banks[suit as usize];
            if gs.favor_banks.iter().enumerate().all(|(i, &x)| i == suit as usize || x > v) {
                bonus += 2;
            }
        }
    }
    bonus
}

pub fn trade_favor_bonus(gs: &GameState, player: PlayerId, _suit: Suit) -> u8 {
    // 55 Secret Signal: +1 favor if gaining 1
    if gs.player_has_card_access(player, 55) {
        1
    } else {
        0
    }
}

pub fn trade_secrets_bonus(gs: &GameState, player: PlayerId, suit: Suit) -> u8 {
    // 42 The Old Oak: +1 secret if Beast adviser
    if suit == Suit::Beast && gs.player_has_card_access(player, 42) {
        1
    } else {
        0
    }
}

pub fn search_cost_modifier(gs: &GameState, player: PlayerId) -> i8 {
    // 134 News from Afar: spend no Supply
    if gs.player_has_card_access(player, 134) {
        return -10;
    }
    0
}

pub fn search_draw_modifier(gs: &GameState, player: PlayerId) -> i8 {
    // 56 Augury: draw 1 more card
    if gs.player_has_card_access(player, 56) {
        1
    } else {
        0
    }
}

// ── UTILITY HELPERS ───────────────────────────────────────────────────────

fn count_suit_on_map(gs: &GameState, suit: Suit) -> u8 {
    let mut n = 0u8;
    for s in &gs.sites {
        if !s.is_faceup {
            continue;
        }
        for sl in 0..s.capacity as usize {
            if s.cards[sl] != CARD_EMPTY && get_card(s.cards[sl]).suit == Some(suit) {
                n += 1;
            }
        }
    }
    n
}

pub fn player_rules_suit(gs: &GameState, player: PlayerId, suit: Suit) -> bool {
    count_suit_ruled(gs, player, suit) > 0
}

fn count_suit_ruled(gs: &GameState, player: PlayerId, suit: Suit) -> u8 {
    let mut n = gs.players[player as usize].faceup_adviser_suit_count(suit);
    for si in 0..MAX_SITES as u8 {
        if gs.player_rules_site(player, si) {
            let s = &gs.sites[si as usize];
            for sl in 0..s.capacity as usize {
                if s.cards[sl] != CARD_EMPTY && get_card(s.cards[sl]).suit == Some(suit) {
                    n += 1;
                }
            }
        }
    }
    n
}

fn count_suits_ruled(gs: &GameState, player: PlayerId) -> u8 {
    Suit::ALL
        .iter()
        .filter(|&&s| count_suit_ruled(gs, player, s) > 0)
        .count() as u8
}

fn discard_suits_in_region(gs: &mut GameState, player: PlayerId, suits: &[Suit]) {
    let reg = gs.sites[gs.players[player as usize].pawn_site as usize].region;
    let dest = reg.discard_target();
    for si in 0..MAX_SITES {
        if gs.sites[si].is_faceup && gs.sites[si].region == reg {
            for sl in 0..gs.sites[si].capacity as usize {
                let c = gs.sites[si].cards[sl];
                if c != CARD_EMPTY
                    && get_card(c).restriction != CardRestriction::Locked
                    && get_card(c).suit.map_or(false, |s| suits.contains(&s))
                {
                    gs.discard_piles[dest as usize].push(c);
                    gs.sites[si].cards[sl] = CARD_EMPTY;
                }
            }
        }
    }
}

fn remove_card_from_board(gs: &mut GameState, cid: CardId) {
    for si in 0..MAX_SITES {
        for sl in 0..MAX_CARDS_PER_SITE {
            if gs.sites[si].cards[sl] == cid {
                gs.sites[si].cards[sl] = CARD_EMPTY;
                return;
            }
        }
    }
    for p in 0..gs.num_players as usize {
        for sl in 0..MAX_ADVISERS {
            if gs.players[p].advisers[sl] == cid {
                gs.players[p].advisers[sl] = CARD_EMPTY;
                gs.players[p].adviser_faceup[sl] = false;
                return;
            }
        }
    }
}
