import { useState } from "react";
import type { CreateGameRequest } from "../types/game";

interface Props {
  onStart: (config: CreateGameRequest) => void;
  loading: boolean;
}

const AGENT_OPTIONS = ["human", "random", "heuristic"];

export default function GameSetup({ onStart, loading }: Props) {
  const [numPlayers, setNumPlayers] = useState(4);
  const [playerTypes, setPlayerTypes] = useState<string[]>([
    "human", "random", "random", "random", "random", "random",
  ]);
  const [seed, setSeed] = useState<string>("42");

  const setPlayerType = (index: number, type: string) => {
    const next = [...playerTypes];
    next[index] = type;
    setPlayerTypes(next);
  };

  const handleStart = () => {
    const humanPlayers: number[] = [];
    const agents: Record<string, string> = {};

    for (let i = 0; i < numPlayers; i++) {
      if (playerTypes[i] === "human") {
        humanPlayers.push(i);
      } else {
        agents[String(i)] = playerTypes[i];
      }
    }

    if (humanPlayers.length === 0) {
      humanPlayers.push(0);
    }

    onStart({
      num_players: numPlayers,
      human_players: humanPlayers,
      agents,
      clockwork_prince: false,
      seed: seed ? parseInt(seed, 10) : null,
    });
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="bg-slate-800 rounded-xl p-8 w-full max-w-md shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-slate-100 mb-6 text-center">
          Oath
        </h1>
        <p className="text-slate-400 text-sm text-center mb-8">
          Chronicles of Empire and Exile
        </p>

        {/* Number of players */}
        <div className="mb-6">
          <label className="block text-slate-300 text-sm font-medium mb-2">
            Players
          </label>
          <div className="flex gap-2">
            {[2, 3, 4, 5, 6].map((n) => (
              <button
                key={n}
                onClick={() => setNumPlayers(n)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  numPlayers === n
                    ? "bg-amber-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        {/* Player slots */}
        <div className="mb-6 space-y-3">
          <label className="block text-slate-300 text-sm font-medium mb-1">
            Player Configuration
          </label>
          {Array.from({ length: numPlayers }, (_, i) => (
            <div
              key={i}
              className="flex items-center gap-3 bg-slate-700/50 rounded-lg px-3 py-2"
            >
              <span className="text-slate-400 text-sm w-12">P{i}</span>
              <span className="text-xs text-slate-500">
                {i === 0 ? "(Chancellor)" : "(Exile)"}
              </span>
              <div className="flex gap-1 ml-auto">
                {AGENT_OPTIONS.map((type) => (
                  <button
                    key={type}
                    onClick={() => setPlayerType(i, type)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      playerTypes[i] === type
                        ? type === "human"
                          ? "bg-sky-600 text-white"
                          : "bg-emerald-700 text-white"
                        : "bg-slate-600 text-slate-300 hover:bg-slate-500"
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Seed */}
        <div className="mb-8">
          <label className="block text-slate-300 text-sm font-medium mb-2">
            Seed (optional)
          </label>
          <input
            type="text"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder="Random"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:border-amber-500"
          />
        </div>

        {/* Start button */}
        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-600 text-white font-bold rounded-lg transition-colors text-lg"
        >
          {loading ? "Starting..." : "Start Game"}
        </button>
      </div>
    </div>
  );
}
