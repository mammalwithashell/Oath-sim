import type { LegalAction, CompoundState } from "../types/game";

interface Props {
  actions: LegalAction[];
  compoundState: CompoundState | null;
  onAction: (actionId: number) => void;
  loading: boolean;
}

// Group actions by type for cleaner display
const ACTION_GROUP_ORDER = [
  "TRAVEL",
  "SEARCH",
  "MUSTER",
  "TRADE_FAVOR",
  "TRADE_SECRETS",
  "RECOVER",
  "RECOVER_PEOPLES_FAVOR",
  "RECOVER_DARKEST_SECRET",
  "CAMPAIGN_DECLARE",
  "MINOR_FLIP_ADVISER",
  "MINOR_USE_ACTION",
  "OFFER_CITIZENSHIP",
  "END_ACT_PHASE",
  // Compound actions
  "SEARCH_PLAY",
  "SEARCH_DISCARD",
  "CAMPAIGN_TARGET_SITE",
  "CAMPAIGN_TARGET_RELIC",
  "CAMPAIGN_TARGET_PAWN",
  "CAMPAIGN_DONE_TARGETS",
  "CAMPAIGN_BATTLE_PLAN",
  "CAMPAIGN_NO_BATTLE",
  "CAMPAIGN_SACRIFICE",
  "ACCEPT_CITIZENSHIP",
  "DECLINE_CITIZENSHIP",
  "SELF_EXILE",
  "RELIQUARY_CHOOSE",
];

const GROUP_LABELS: Record<string, string> = {
  TRAVEL: "Travel",
  SEARCH: "Search",
  MUSTER: "Muster",
  TRADE_FAVOR: "Trade (Favor)",
  TRADE_SECRETS: "Trade (Secrets)",
  RECOVER: "Recover",
  RECOVER_PEOPLES_FAVOR: "Recover",
  RECOVER_DARKEST_SECRET: "Recover",
  CAMPAIGN_DECLARE: "Campaign",
  MINOR_FLIP_ADVISER: "Minor",
  MINOR_USE_ACTION: "Minor",
  OFFER_CITIZENSHIP: "Citizenship",
  END_ACT_PHASE: "End Turn",
  SEARCH_PLAY: "Play Card",
  SEARCH_DISCARD: "Discard",
  CAMPAIGN_TARGET_SITE: "Target",
  CAMPAIGN_TARGET_RELIC: "Target",
  CAMPAIGN_TARGET_PAWN: "Target",
  CAMPAIGN_DONE_TARGETS: "Done",
  CAMPAIGN_BATTLE_PLAN: "Battle Plan",
  CAMPAIGN_NO_BATTLE: "Skip",
  CAMPAIGN_SACRIFICE: "Sacrifice",
  ACCEPT_CITIZENSHIP: "Respond",
  DECLINE_CITIZENSHIP: "Respond",
  SELF_EXILE: "Self-Exile",
  RELIQUARY_CHOOSE: "Reliquary",
};

const GROUP_BUTTON_COLORS: Record<string, string> = {
  TRAVEL: "bg-emerald-800/60 hover:bg-emerald-700/60 border-emerald-700/50",
  SEARCH: "bg-blue-800/60 hover:bg-blue-700/60 border-blue-700/50",
  MUSTER: "bg-amber-800/60 hover:bg-amber-700/60 border-amber-700/50",
  CAMPAIGN_DECLARE: "bg-red-800/60 hover:bg-red-700/60 border-red-700/50",
  END_ACT_PHASE: "bg-slate-700/80 hover:bg-slate-600/80 border-slate-600/50",
};

function getButtonColor(actionType: string): string {
  // Check exact match first, then prefix match
  if (GROUP_BUTTON_COLORS[actionType]) return GROUP_BUTTON_COLORS[actionType];
  if (actionType.startsWith("CAMPAIGN")) return "bg-red-800/60 hover:bg-red-700/60 border-red-700/50";
  if (actionType.startsWith("SEARCH")) return "bg-blue-800/60 hover:bg-blue-700/60 border-blue-700/50";
  if (actionType.startsWith("TRADE")) return "bg-purple-800/60 hover:bg-purple-700/60 border-purple-700/50";
  if (actionType.startsWith("RECOVER")) return "bg-amber-800/60 hover:bg-amber-700/60 border-amber-700/50";
  if (actionType.startsWith("MINOR")) return "bg-teal-800/60 hover:bg-teal-700/60 border-teal-700/50";
  if (actionType.includes("CITIZENSHIP")) return "bg-sky-800/60 hover:bg-sky-700/60 border-sky-700/50";
  return "bg-slate-700/60 hover:bg-slate-600/60 border-slate-600/50";
}

export default function ActionPanel({ actions, compoundState, onAction, loading }: Props) {
  if (actions.length === 0) return null;

  // Compound state header
  const compoundHeader = compoundState ? getCompoundHeader(compoundState) : null;

  // Group actions
  const grouped = new Map<string, LegalAction[]>();
  for (const action of actions) {
    const group = GROUP_LABELS[action.action_type] || action.action_type;
    if (!grouped.has(group)) grouped.set(group, []);
    grouped.get(group)!.push(action);
  }

  // Sort groups
  const sortedGroups = [...grouped.entries()].sort((a, b) => {
    const aIdx = ACTION_GROUP_ORDER.findIndex((t) => GROUP_LABELS[t] === a[0]);
    const bIdx = ACTION_GROUP_ORDER.findIndex((t) => GROUP_LABELS[t] === b[0]);
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
  });

  return (
    <div className="bg-slate-800/80 rounded-lg border border-slate-700 p-4">
      {compoundHeader && (
        <div className="text-sm font-medium text-amber-400 mb-3 pb-2 border-b border-slate-700">
          {compoundHeader}
        </div>
      )}

      <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
        {compoundState ? "Choose Action" : "Your Turn"}
      </h3>

      <div className="space-y-3">
        {sortedGroups.map(([group, groupActions]) => (
          <div key={group}>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">
              {group}
            </span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {groupActions.map((action) => (
                <button
                  key={action.action_id}
                  onClick={() => onAction(action.action_id)}
                  disabled={loading}
                  className={`px-3 py-1.5 rounded-md border text-xs text-slate-200 transition-colors disabled:opacity-50 ${getButtonColor(action.action_type)}`}
                >
                  {action.description}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getCompoundHeader(cs: CompoundState): string | null {
  switch (cs.state_type) {
    case "SEARCH_CHOOSE":
      return `Search Results (from ${cs.search_source || "deck"})`;
    case "CAMPAIGN_TARGETS":
      return `Campaign: P${cs.campaign_attacker} attacking P${cs.campaign_defender} - Select Targets`;
    case "CAMPAIGN_BATTLE":
      return `Campaign Battle: ATK ${cs.campaign_attack_dice} dice vs DEF ${cs.campaign_defense_dice} dice`;
    case "CAMPAIGN_SACRIFICE":
      return `Campaign Lost - Sacrifice Warbands?`;
    case "CITIZENSHIP_RESPONSE":
      return `P${cs.citizenship_offerer} offers you citizenship`;
    case "RELIQUARY_CHOOSE":
      return "Choose a Relic from the Reliquary";
    default:
      return null;
  }
}
