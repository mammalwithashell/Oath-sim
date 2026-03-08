import { useEffect, useRef } from "react";
import type { ActionLogEntry } from "../types/game";
import { PLAYER_COLORS } from "../types/game";

interface Props {
  log: ActionLogEntry[];
  aiActions: ActionLogEntry[];
  visibleAiActionCount: number;
  isAnimating: boolean;
}

export default function GameLog({ log, aiActions, visibleAiActionCount, isAnimating }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // During animation, only show up to visibleAiActionCount of the AI actions.
  // The log contains both old entries + new AI entries at the end.
  // We need to hide AI entries beyond visibleAiActionCount.

  const aiStartIndex = log.length - aiActions.length;
  const visibleLog = isAnimating
    ? log.slice(-50).filter((_, i) => {
        const globalIdx = log.length - 50 + i;
        if (globalIdx < 0) return false;
        // If this entry is part of the AI batch, check if it's visible yet
        const aiIdx = globalIdx - aiStartIndex;
        if (aiIdx >= 0 && aiIdx < aiActions.length) {
          return aiIdx < visibleAiActionCount;
        }
        return true;
      })
    : log.slice(-50);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleLog.length]);

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
        {visibleLog.map((entry, i) => {
          const isLatestAnimating = isAnimating && i === visibleLog.length - 1;
          const isNew = !isAnimating && aiActions.some(
            (a) => a.action_id === entry.action_id && a.player === entry.player && a.description === entry.description
          );
          return (
            <div
              key={i}
              className={`flex items-start gap-1.5 transition-colors duration-200 ${
                entry.is_human
                  ? "text-sky-300"
                  : isLatestAnimating
                  ? "text-amber-300 font-medium"
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
        {visibleLog.length === 0 && (
          <span className="text-slate-600">Game starting...</span>
        )}
      </div>
    </div>
  );
}
