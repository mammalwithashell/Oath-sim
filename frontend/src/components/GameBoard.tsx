import type { GameResponse } from "../types/game";
import BannerBar from "./BannerBar";
import MapView from "./MapView";
import PlayerPanel from "./PlayerPanel";
import ActionPanel from "./ActionPanel";
import GameLog from "./GameLog";
import GameOverModal from "./GameOverModal";

interface Props {
  data: GameResponse;
  onAction: (actionId: number) => void;
  onNewGame: () => void;
  loading: boolean;
}

export default function GameBoard({ data, onAction, onNewGame, loading }: Props) {
  const gs = data.game_state;

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col">
      <BannerBar gs={gs} humanPlayerIndex={data.human_player_index} />

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Map */}
        <div className="flex-1 p-4 overflow-y-auto">
          <MapView sites={gs.sites} players={gs.players} />
        </div>

        {/* Right: Players + Actions + Log */}
        <div className="w-[380px] flex flex-col border-l border-slate-700 overflow-y-auto">
          {/* Players */}
          <div className="p-3 space-y-2">
            {gs.players.map((player) => (
              <PlayerPanel
                key={player.index}
                player={player}
                isCurrentTurn={player.index === gs.current_player_index}
                isHuman={player.index === data.human_player_index}
              />
            ))}
          </div>

          {/* Actions */}
          {data.is_human_turn && (
            <div className="px-3 pb-3">
              <ActionPanel
                actions={data.legal_actions}
                compoundState={gs.compound_state}
                onAction={onAction}
                loading={loading}
              />
            </div>
          )}

          {!data.is_human_turn && !gs.is_game_over && (
            <div className="px-3 pb-3">
              <div className="bg-slate-800/60 rounded-lg border border-slate-700 p-4 text-center">
                <span className="text-slate-400 text-sm">
                  Waiting for AI players...
                </span>
              </div>
            </div>
          )}

          {/* Log */}
          <div className="px-3 pb-3 mt-auto">
            <GameLog log={data.action_log} aiActions={data.ai_actions} />
          </div>
        </div>
      </div>

      {/* Game over overlay */}
      <GameOverModal
        gs={gs}
        humanPlayerIndex={data.human_player_index}
        onNewGame={onNewGame}
      />
    </div>
  );
}
