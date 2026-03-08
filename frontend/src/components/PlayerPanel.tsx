import type { PlayerState } from "../types/game";
import { ROLE_COLORS, ROLE_BG_COLORS, SUIT_COLORS, PLAYER_COLORS } from "../types/game";

interface Props {
  player: PlayerState;
  isCurrentTurn: boolean;
  isHuman: boolean;
}

export default function PlayerPanel({ player, isCurrentTurn, isHuman }: Props) {
  const roleColor = ROLE_COLORS[player.role] || "text-slate-300";
  const bgColor = ROLE_BG_COLORS[player.role] || "bg-slate-800 border-slate-600";

  return (
    <div
      className={`rounded-lg border p-3 ${bgColor} ${
        isCurrentTurn ? "ring-2 ring-amber-400/60" : ""
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`w-5 h-5 rounded-full ${PLAYER_COLORS[player.index]} flex items-center justify-center text-[10px] text-white font-bold`}
        >
          {player.index}
        </span>
        <span className={`font-bold text-sm ${roleColor}`}>
          {player.role}
        </span>
        {isHuman && (
          <span className="text-xs text-sky-400 bg-sky-900/40 px-1.5 py-0.5 rounded">
            You
          </span>
        )}
        {isCurrentTurn && (
          <span className="text-xs text-amber-400 ml-auto">Active</span>
        )}
      </div>

      {/* Location */}
      <div className="text-xs text-slate-400 mb-2">
        @ {player.site_name}
      </div>

      {/* Resources */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs mb-2">
        <span className="text-slate-400">
          Supply: <span className="text-slate-200">{player.supply}</span>
        </span>
        <span className="text-slate-400">
          Favor: <span className="text-amber-300">{player.favor}</span>
        </span>
        <span className="text-slate-400">
          Secrets: <span className="text-indigo-300">{player.secrets}</span>
        </span>
        <span className="text-slate-400">
          WB: <span className="text-slate-200">{player.warbands_bank}+{player.warbands_board}</span>
        </span>
      </div>

      {/* Advisers */}
      {player.advisers.length > 0 && (
        <div className="space-y-0.5 mb-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">
            Advisers
          </span>
          {player.advisers.map((adv, i) => (
            <div key={i} className="flex items-center gap-1 text-xs">
              <span className="text-slate-600">[{adv.slot ?? i}]</span>
              <span className={adv.suit ? (SUIT_COLORS[adv.suit] || "text-slate-400") : "text-slate-400"}>
                {adv.name}
              </span>
              <span className="text-slate-600">
                {adv.faceup ? "^" : "v"}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Relics */}
      {player.relics.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-1">
          {player.relics.map((r, i) => r && (
            <span
              key={i}
              className="text-[10px] bg-amber-900/30 text-amber-300 px-1 py-0.5 rounded"
            >
              {r.name}
            </span>
          ))}
        </div>
      )}

      {/* Vision */}
      {player.vision && (
        <div className="text-xs text-purple-300 mt-1">
          Vision: {player.vision.name}
        </div>
      )}

      {/* Sites ruled */}
      {player.num_sites_ruled > 0 && (
        <div className="text-xs text-slate-500 mt-1">
          Sites ruled: {player.num_sites_ruled}
        </div>
      )}
    </div>
  );
}
