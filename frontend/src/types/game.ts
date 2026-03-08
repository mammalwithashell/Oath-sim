export interface CardInfo {
  id: number | null;
  name: string;
  suit: string | null;
  is_vision: boolean;
  is_relic: boolean;
  is_site: boolean;
  is_edifice: boolean;
  favor?: number;
  secrets?: number;
  faceup?: boolean;
  slot?: number;
  remaining?: boolean;
}

export interface SiteState {
  index: number;
  name: string;
  region: string;
  defense: number;
  is_faceup: boolean;
  capacity: number;
  ruling_player: number | null;
  warbands: number;
  cards: (CardInfo | null)[];
  relics: (CardInfo | null)[];
  pawns: number[];
}

export interface PlayerState {
  index: number;
  role: string;
  pawn_site: number;
  site_name: string;
  supply: number;
  favor: number;
  secrets: number;
  warbands_bank: number;
  warbands_board: number;
  advisers: CardInfo[];
  relics: (CardInfo | null)[];
  vision: CardInfo | null;
  num_sites_ruled: number;
}

export interface CompoundState {
  state_type: string;
  drawn_cards?: CardInfo[];
  search_source?: string;
  campaign_attacker?: number;
  campaign_defender?: number;
  campaign_targets?: string[];
  campaign_attack_dice?: number;
  campaign_defense_dice?: number;
  campaign_attack_result?: number;
  campaign_defense_result?: number;
  citizenship_offerer?: number;
  citizenship_target?: number;
}

export interface GameState {
  round_number: number;
  phase: string;
  oath_goal: string;
  successor_goal: string;
  current_player_index: number;
  num_players: number;
  is_game_over: boolean;
  winner: number | null;
  win_type: string | null;
  oathkeeper_holder: number | null;
  oathkeeper_side: string;
  peoples_favor: { holder: number | null; tokens: number };
  darkest_secret: { holder: number | null; tokens: number };
  favor_banks: Record<string, number>;
  shared_secrets: number;
  world_deck_size: number;
  relic_deck_size: number;
  sites: SiteState[];
  players: PlayerState[];
  compound_state: CompoundState | null;
}

export interface LegalAction {
  action_id: number;
  action_type: string;
  description: string;
}

export interface ActionLogEntry {
  player: number;
  role: string;
  action_id: number;
  description: string;
  is_human?: boolean;
}

export interface GameResponse {
  game_id: string;
  game_state: GameState;
  is_human_turn: boolean;
  human_player_index: number | null;
  legal_actions: LegalAction[];
  ai_actions: ActionLogEntry[];
  action_log: ActionLogEntry[];
}

export interface CreateGameRequest {
  num_players: number;
  human_players: number[];
  agents: Record<string, string>;
  clockwork_prince: boolean;
  seed: number | null;
}

// Suit color mapping for Tailwind classes
export const SUIT_COLORS: Record<string, string> = {
  Discord: "text-purple-400",
  Arcane: "text-blue-400",
  Order: "text-yellow-400",
  Hearth: "text-red-400",
  Beast: "text-green-400",
  Nomad: "text-orange-400",
};

export const SUIT_BG_COLORS: Record<string, string> = {
  Discord: "bg-purple-900/40",
  Arcane: "bg-blue-900/40",
  Order: "bg-yellow-900/40",
  Hearth: "bg-red-900/40",
  Beast: "bg-green-900/40",
  Nomad: "bg-orange-900/40",
};

export const SUIT_DOT_COLORS: Record<string, string> = {
  Discord: "bg-purple-400",
  Arcane: "bg-blue-400",
  Order: "bg-yellow-400",
  Hearth: "bg-red-400",
  Beast: "bg-green-400",
  Nomad: "bg-orange-400",
};

export const ROLE_COLORS: Record<string, string> = {
  CHANCELLOR: "text-amber-400",
  EXILE: "text-slate-300",
  CITIZEN: "text-sky-400",
};

export const ROLE_BG_COLORS: Record<string, string> = {
  CHANCELLOR: "bg-amber-900/40 border-amber-500/50",
  EXILE: "bg-slate-800/60 border-slate-500/50",
  CITIZEN: "bg-sky-900/40 border-sky-500/50",
};

export const PLAYER_COLORS = [
  "bg-red-500",
  "bg-blue-500",
  "bg-green-500",
  "bg-yellow-500",
  "bg-purple-500",
  "bg-pink-500",
];

export const REGION_COLORS: Record<string, string> = {
  CRADLE: "border-l-amber-500",
  PROVINCES: "border-l-emerald-500",
  HINTERLAND: "border-l-slate-500",
};
