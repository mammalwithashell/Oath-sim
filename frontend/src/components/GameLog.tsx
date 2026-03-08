import { useEffect, useRef } from "react";
import type { ActionLogEntry } from "../types/game";
import { PLAYER_COLORS } from "../types/game";

interface Props {
  log: ActionLogEntry[];
  aiActions: ActionLogEntry[];
}

export default function GameLog({ log, aiActions }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [log.length]);

  // Show the last 50 entries to avoid overwhelming the UI
  const recentLog = log.slice(-50);

  return (
    <div className="bg-slate-800/60 rounded-lg border border-slate-700">
      <div className="px-3 py-2 border-b border-slate-700">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
          Game Log
        </h3>
      </div>
      <div
        ref={scrollRef}
        className="p-2 max-h-48 overflow-y-auto space-y-0.5 text-xs font-mono"
      >
        {recentLog.map((entry, i) => {
          const isNew = aiActions.some(
            (a) => a.action_id === entry.action_id && a.player === entry.player && a.description === entry.description
          );
          return (
            <div
              key={i}
              className={`flex items-start gap-1.5 ${
                entry.is_human
                  ? "text-sky-300"
                  : isNew
                  ? "text-slate-200"
                  : "text-slate-500"
              }`}
            >
              <span
                className={`w-4 h-4 rounded-full ${PLAYER_COLORS[entry.player]} flex-shrink-0 flex items-center justify-center text-[8px] text-white font-bold mt-0.5`}
              >
                {entry.player}
              </span>
              <span className="text-slate-600">{entry.role[0]}</span>
              <span>{entry.description}</span>
            </div>
          );
        })}
        {recentLog.length === 0 && (
          <span className="text-slate-600">Game starting...</span>
        )}
      </div>
    </div>
  );
}
