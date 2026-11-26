export interface CardMeta {
  id: number;
  name: string;
  suit: string;
  text: string;
}

export interface SiteState {
  site_id: number;
  region: string;
  is_faceup: boolean;
  capacity: number;
  cards: number[];
  card_favor: number[];
  card_secrets: number[];
  relics: number[];
  ruling_player: number | null;
  warbands: number;
  warband_color: number | null;
  site_favor: number;
  site_secrets: number;
  site_meta: CardMeta | null;
  card_metas: (CardMeta | null)[];
  relic_metas: (CardMeta | null)[];
}

export interface PlayerState {
  role: string;
  pawn_site: number;
  supply: number;
  warbands_board: number;
  warbands_bank: number;
  favor: number;
  secrets_faceup: number;
  secrets_facedown: number;
  advisers: number[];
  adviser_faceup: boolean[];
  relics: number[];
  revealed_vision: number | null;
  color: number;
  talk_remaining: number;
  adviser_metas: (CardMeta | null)[];
  relic_metas: (CardMeta | null)[];
}

export interface DealBundle {
  favor: number;
  secrets: number;
  relics: number[];
  advisers: number[];
  sites: number[];
  banners: string[];
  reliquary_slot: number | null;
  warbands: number;
}

export interface DealState {
  kind: string;
  initiator: number;
  proposer: number;
  responder: number;
  round: number;
  offer: DealBundle;
  request: DealBundle;
  contracts: TribunalContract[];
  allow_reliquary_peek: boolean;
}

export interface TribunalContract {
  party_a: number;
  party_b: number;
  clause: Record<string, unknown>;
  enforcement: string | Record<string, unknown>;
  fulfilled: boolean;
}

export interface TalkEvent {
  round: number;
  sender: number;
  target: number | null;
  intent: string;
  suit: string | null;
  shown_card: number | null;
}

export interface LegalAction {
  action_id: number;
  category: string;
  description: string;
}

export interface AiInspector {
  player: number;
  agent: string;
  win_probs: number[];
  top_actions: { action_id: number; description: string; prob: number }[];
}

export interface ActionLogEntry {
  player: number;
  seat: string;
  action_id: number;
  description: string;
}

export interface RustGameState {
  num_players: number;
  current_player: number;
  round_number: number;
  visions_drawn: number;
  phase: string;
  oath_goal: string;
  successor_goal: string;
  oathkeeper_holder: number | null;
  oathkeeper_side: string;
  peoples_favor_holder: number | null;
  peoples_favor_tokens: number;
  peoples_favor_is_mob: boolean;
  darkest_secret_holder: number | null;
  darkest_secret_tokens: number;
  favor_banks: number[];
  shared_secrets: number;
  world_deck: number[];
  relic_deck: number[];
  reliquary: number[];
  sites: SiteState[];
  players: PlayerState[];
  decision: string | Record<string, unknown>;
  deal: DealState | null;
  active_contracts: TribunalContract[];
  talk_log: TalkEvent[];
  is_game_over: boolean;
  winner: number | null;
  win_type: string | null;
}

export interface GamePayload {
  game_id: string;
  seats: string[];
  acting_player: number | null;
  is_human_turn: boolean;
  state: RustGameState;
  legal_actions: LegalAction[];
  ai_actions: ActionLogEntry[];
  action_log: ActionLogEntry[];
  ai_inspector: AiInspector | null;
}

export interface CreateGameConfig {
  num_players: number;
  seats: string[];
  seat_checkpoints?: (string | null)[];
  seed: number;
  first_game: boolean;
  oath_goal: number | null;
  chronicle_enabled: boolean;
  staged_sites?: number[] | null;
  staged_reliquary?: number[] | null;
  staged_chancellor_relics?: number[] | null;
  chronicle_json?: string | null;
}

export interface ModelInfo {
  name: string;
  path: string;
}

export interface CatalogData {
  sites: CardMeta[];
  relics: CardMeta[];
}

export interface ReplaySummary {
  replay_id: string;
  name: string;
  created_at: number;
  num_players: number;
  seats: string[];
  num_chronicles: number;
}

export interface ReplayFrame {
  step: number;
  actor: number | null;
  action_id: number | null;
  description: string;
  ai_inspector: AiInspector | null;
  state: RustGameState;
}

export interface ReplayChronicle {
  chronicle_number: number;
  oath_goal: string;
  winner: number | null;
  win_type: string | null;
  vowed_oath: string | null;
  rounds: number;
  num_frames: number;
  chronicle_json: string;
  frames: ReplayFrame[];
}

export interface ReplayDoc {
  replay_id: string;
  name: string;
  created_at: number;
  num_players: number;
  seats: string[];
  seat_checkpoints: (string | null)[];
  num_chronicles: number;
  chronicles: ReplayChronicle[];
}
