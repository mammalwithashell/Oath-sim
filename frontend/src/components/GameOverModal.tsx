import type { GameState } from "../types/game";
import { ROLE_COLORS, PLAYER_COLORS } from "../types/game";

interface Props {
  gs: GameState;
  humanPlayerIndex: number | null;
  onNewGame: () => void;
}

export default function GameOverModal({ gs, humanPlayerIndex, onNewGame }: Props) {
  if (!gs.is_game_over || gs.winner === null) return null;

  const winner = gs.players[gs.winner];
  const isHumanWin = gs.winner === humanPlayerIndex;
  const roleColor = ROLE_COLORS[winner.role] || "text-slate-300";

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl p-8 max-w-sm w-full shadow-2xl border border-slate-600 text-center">
        <h2 className="text-2xl font-bold text-slate-100 mb-4">
          Game Over
        </h2>

        <div className="mb-4">
          <span
            className={`w-12 h-12 rounded-full ${PLAYER_COLORS[gs.winner]} inline-flex items-center justify-center text-xl text-white font-bold`}
          >
            {gs.winner}
          </span>
        </div>

        <p className="text-lg mb-2">
          <span className={`font-bold ${roleColor}`}>
            P{gs.winner} ({winner.role})
          </span>{" "}
          wins!
        </p>

        {isHumanWin && (
          <p className="text-amber-400 text-lg font-bold mb-2">
            Victory is yours!
          </p>
        )}

        <p className="text-slate-400 text-sm mb-1">
          Win type: {gs.win_type || "Unknown"}
        </p>
        <p className="text-slate-500 text-sm mb-6">
          Round {gs.round_number}/8
        </p>

        <button
          onClick={onNewGame}
          className="px-6 py-2 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-lg transition-colors"
        >
          New Game
        </button>
      </div>
    </div>
  );
}
