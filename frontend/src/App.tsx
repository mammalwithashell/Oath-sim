import { useState } from "react";
import { useRustGame } from "./hooks/useRustGame";
import RustGameSetup from "./components/RustGameSetup";
import RustGameBoard from "./components/RustGameBoard";
import ReplayViewer from "./components/ReplayViewer";

export default function App() {
  const { payload, loading, error, startGame, sendAction, loadPayload, resetGame } = useRustGame();
  const [view, setView] = useState<"play" | "replays">("play");

  if (view === "replays" && !payload) {
    return (
      <ReplayViewer
        onBackToSetup={() => setView("play")}
        onTakeoverGame={(data) => {
          loadPayload(data);
          setView("play");
        }}
      />
    );
  }

  if (!payload) {
    return (
      <div>
        <RustGameSetup
          onStart={startGame}
          onOpenReplays={() => setView("replays")}
          loading={loading}
        />
        {error && (
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-red-900 text-red-100 px-4 py-2 rounded-lg text-sm shadow-lg">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <RustGameBoard
        payload={payload}
        loading={loading}
        onAction={sendAction}
        onNewGame={resetGame}
      />
      {error && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-red-900 text-red-100 px-4 py-2 rounded-lg text-sm shadow-lg z-50">
          {error}
        </div>
      )}
    </div>
  );
}
