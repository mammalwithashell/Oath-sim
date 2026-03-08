import type { GameState } from "../types/game";

interface Props {
  gs: GameState;
  humanPlayerIndex: number | null;
}

export default function BannerBar({ gs, humanPlayerIndex }: Props) {
  const formatHolder = (holder: number | null, tokens: number) => {
    if (holder === null) return `Unclaimed (${tokens})`;
    return `P${holder} (${tokens})`;
  };

  return (
    <div className="bg-slate-800 border-b border-slate-700 px-4 py-3">
      {/* Top row: Oath info */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-4">
          <h2 className="text-amber-400 font-bold text-lg">
            Oath of {gs.oath_goal}
          </h2>
          <span className="text-slate-400 text-sm">
            Round {gs.round_number}/8
          </span>
          <span className="text-slate-500 text-sm">
            Successor: {gs.successor_goal}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-400">
            Deck: {gs.world_deck_size}
          </span>
          <span className="text-slate-400">
            Relics: {gs.relic_deck_size}
          </span>
          {humanPlayerIndex !== null && (
            <span className="text-sky-400 font-medium">
              You are P{humanPlayerIndex}
            </span>
          )}
        </div>
      </div>

      {/* Bottom row: Banners + Favor banks */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-4">
          <span className="text-slate-300">
            <span className="text-slate-500">PF:</span>{" "}
            {formatHolder(gs.peoples_favor.holder, gs.peoples_favor.tokens)}
          </span>
          <span className="text-slate-300">
            <span className="text-slate-500">DS:</span>{" "}
            {formatHolder(gs.darkest_secret.holder, gs.darkest_secret.tokens)}
          </span>
          <span className="text-slate-300">
            <span className="text-slate-500">Oathkeeper:</span>{" "}
            {gs.oathkeeper_holder !== null ? `P${gs.oathkeeper_holder}` : "none"}{" "}
            <span className="text-slate-500">({gs.oathkeeper_side})</span>
          </span>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          {Object.entries(gs.favor_banks).map(([suit, count]) => (
            <span key={suit} className="text-slate-400">
              <span className={suitTextColor(suit)}>{suit[0]}</span>
              :{count}
            </span>
          ))}
          <span className="text-slate-400 ml-1">
            Secrets:{gs.shared_secrets}
          </span>
        </div>
      </div>
    </div>
  );
}

function suitTextColor(suit: string): string {
  const map: Record<string, string> = {
    Discord: "text-purple-400",
    Arcane: "text-blue-400",
    Order: "text-yellow-400",
    Hearth: "text-red-400",
    Beast: "text-green-400",
    Nomad: "text-orange-400",
  };
  return map[suit] || "text-slate-400";
}
