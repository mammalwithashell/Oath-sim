import type { SiteState, PlayerState } from "../types/game";
import { SUIT_COLORS, SUIT_DOT_COLORS, PLAYER_COLORS, REGION_COLORS } from "../types/game";

interface Props {
  site: SiteState;
  players: PlayerState[];
  isHighlighted?: boolean;
  highlightedSlots?: Set<number> | null;
}

const GLOW_SITE = "ring-2 ring-amber-400/70 shadow-[0_0_20px_rgba(251,191,36,0.3)]";
const GLOW_SLOT = "bg-amber-400/15 rounded-sm";

export default function SiteCard({ site, players, isHighlighted, highlightedSlots }: Props) {
  const regionColor = REGION_COLORS[site.region] || "border-l-slate-600";
  const glowClass = isHighlighted ? GLOW_SITE : "";

  if (!site.is_faceup) {
    return (
      <div className={`bg-slate-800/80 rounded-lg border border-slate-700 border-l-4 ${regionColor} p-3 min-w-[220px] transition-shadow duration-300 ${glowClass}`}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-slate-400 font-medium text-sm">{site.name}</span>
          <span className="text-xs text-slate-600">FACEDOWN</span>
        </div>
        {site.pawns.length > 0 && (
          <div className="flex gap-1 mt-2">
            {site.pawns.map((p) => (
              <span
                key={p}
                className={`w-4 h-4 rounded-full ${PLAYER_COLORS[p]} flex items-center justify-center text-[9px] text-white font-bold`}
              >
                {p}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`bg-slate-800/80 rounded-lg border border-slate-700 border-l-4 ${regionColor} p-3 min-w-[220px] transition-shadow duration-300 ${glowClass}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-200 font-medium text-sm">{site.name}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 bg-slate-700 px-1.5 py-0.5 rounded">
            DEF {site.defense}
          </span>
        </div>
      </div>

      {/* Ruler */}
      {site.ruling_player !== null && (
        <div className="text-xs text-slate-400 mb-2">
          Ruler: P{site.ruling_player} ({site.warbands} wb)
        </div>
      )}

      {/* Cards */}
      <div className="space-y-1 mb-2">
        {site.cards.map((card, slot) => {
          const slotGlow = highlightedSlots?.has(slot) ? GLOW_SLOT : "";
          return (
            <div key={slot} className={`flex items-center gap-1.5 text-xs px-1 py-0.5 -mx-1 transition-colors duration-300 ${slotGlow}`}>
              <span className="text-slate-600 w-4">[{slot}]</span>
              {card ? (
                <>
                  <span className={`w-2 h-2 rounded-full ${card.suit ? SUIT_DOT_COLORS[card.suit] : "bg-slate-600"}`} />
                  <span className={card.suit ? SUIT_COLORS[card.suit] : "text-slate-400"}>
                    {card.name}
                  </span>
                  {(card.favor ?? 0) > 0 && (
                    <span className="text-amber-400">+{card.favor}f</span>
                  )}
                  {(card.secrets ?? 0) > 0 && (
                    <span className="text-indigo-400">+{card.secrets}s</span>
                  )}
                </>
              ) : (
                <span className="text-slate-600">--</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Relics */}
      {site.relics.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {site.relics.map((r, i) => r && (
            <span
              key={i}
              className="text-xs bg-amber-900/30 text-amber-300 px-1.5 py-0.5 rounded border border-amber-800/50"
            >
              {r.name}
            </span>
          ))}
        </div>
      )}

      {/* Pawns */}
      {site.pawns.length > 0 && (
        <div className="flex gap-1">
          {site.pawns.map((p) => (
            <span
              key={p}
              className={`w-5 h-5 rounded-full ${PLAYER_COLORS[p]} flex items-center justify-center text-[10px] text-white font-bold`}
              title={`P${p} (${players[p]?.role})`}
            >
              {p}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
