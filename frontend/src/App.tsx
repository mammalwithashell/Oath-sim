import { useGame } from "./hooks/useGame";
import GameSetup from "./components/GameSetup";
import GameBoard from "./components/GameBoard";

export default function App() {
  const { gameData, loading, error, startGame, takeAction, resetGame } = useGame();

  if (!gameData) {
    return (
      <div>
        <GameSetup onStart={startGame} loading={loading} />
        {error && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-red-900 text-red-200 px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <GameBoard
        data={gameData}
        onAction={takeAction}
        onNewGame={resetGame}
        loading={loading}
      />
      {error && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-red-900 text-red-200 px-4 py-2 rounded-lg text-sm z-50">
          {error}
        </div>
      )}
    </div>
  );
}
