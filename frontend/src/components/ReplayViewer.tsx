import { useEffect, useState } from "react";
import type {
  GamePayload,
  ModelInfo,
  ReplayDoc,
  ReplaySummary,
} from "../types/rustGame";

const AI_SEAT_OPTIONS = [
  { value: "lstm", label: "LSTM (PyTorch)" },
  { value: "mcts", label: "IS-MCTS (Rust)" },
  { value: "heuristic", label: "Role-Aware Bot (Rust)" },
  { value: "random", label: "Random" },
];

const SUIT_COLORS: Record<string, string> = {
  Discord: "bg-purple-500",
  Arcane: "bg-blue-500",
  Order: "bg-yellow-400",
  Hearth: "bg-red-500",
  Beast: "bg-green-500",
  Nomad: "bg-orange-500",
  None: "bg-slate-500",
};

const PLAYER_COLORS = [
  "bg-amber-400 text-slate-950",
  "bg-emerald-400 text-slate-950",
  "bg-sky-400 text-slate-950",
  "bg-rose-400 text-slate-950",
  "bg-violet-400 text-slate-950",
  "bg-teal-400 text-slate-950",
];

interface Props {
  onBackToSetup: () => void;
  onTakeoverGame: (payload: GamePayload) => void;
}

export default function ReplayViewer({ onBackToSetup, onTakeoverGame }: Props) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [replays, setReplays] = useState<ReplaySummary[]>([]);
  const [activeReplay, setActiveReplay] = useState<ReplayDoc | null>(null);
  const [chronicleIdx, setChronicleIdx] = useState(0);
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(500);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Simulation config
  const [numPlayers, setNumPlayers] = useState(4);
  const [numChronicles, setNumChronicles] = useState(3);
  const [oathGoal, setOathGoal] = useState<string>("0");
  const [seed, setSeed] = useState(42);
  const [seats, setSeats] = useState<string[]>([
    "lstm",
    "lstm",
    "heuristic",
    "mcts",
    "heuristic",
    "heuristic",
  ]);
  const [seatCkpts, setSeatCkpts] = useState<(string | null)[]>([
    null,
    null,
    null,
    null,
    null,
    null,
  ]);
  const [chronicleImport, setChronicleImport] = useState("");
  const [takeoverSeat, setTakeoverSeat] = useState(1);

  const refreshReplays = () => {
    fetch("/api/replays")
      .then((r) => r.json())
      .then((d) => setReplays(d.replays || []))
      .catch(() => {});
  };

  useEffect(() => {
    refreshReplays();
    fetch("/api/models")
      .then((r) => r.json())
      .then((d) => {
        const list: ModelInfo[] = d.models || [];
        setModels(list);
        if (list.length > 0) {
          const def = list.find((m) => m.name.includes("best"))?.path ?? list[0].path;
          setSeatCkpts((prev) => prev.map((v) => v ?? def));
        }
      })
      .catch(() => {});
  }, []);

  const currentChronicle = activeReplay?.chronicles[chronicleIdx] ?? null;
  const currentFrame = currentChronicle?.frames[frameIdx] ?? null;

  useEffect(() => {
    if (!playing || !currentChronicle) return;
    const id = window.setInterval(() => {
      setFrameIdx((prev) => {
        if (prev + 1 >= currentChronicle.frames.length) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, speedMs);
    return () => window.clearInterval(id);
  }, [playing, speedMs, currentChronicle]);

  const loadReplay = async (replayId: string) => {
    setPlaying(false);
    setError(null);
    const res = await fetch(`/api/replays/${replayId}`);
    if (!res.ok) {
      setError("Failed to load replay");
      return;
    }
    const doc: ReplayDoc = await res.json();
    setActiveReplay(doc);
    setChronicleIdx(0);
    setFrameIdx(0);
  };

  const runSimulation = async () => {
    setSimulating(true);
    setError(null);
    try {
      const res = await fetch("/api/replays/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          num_players: numPlayers,
          num_chronicles: numChronicles,
          seats: seats.slice(0, numPlayers),
          seat_checkpoints: seatCkpts.slice(0, numPlayers),
          seed,
          first_game: true,
          oath_goal: oathGoal === "" ? null : Number(oathGoal),
          chronicle_json: chronicleImport.trim() ? chronicleImport.trim() : null,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      refreshReplays();
      await loadReplay(data.replay_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setSimulating(false);
    }
  };

  const handleTakeover = async () => {
    if (!activeReplay) return;
    setPlaying(false);
    const newSeats = [...activeReplay.seats];
    newSeats[takeoverSeat] = "human";
    const res = await fetch(`/api/replays/${activeReplay.replay_id}/takeover`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chronicle_index: chronicleIdx,
        frame_index: frameIdx,
        seats: newSeats,
        seat_checkpoints: activeReplay.seat_checkpoints,
      }),
    });
    if (!res.ok) {
      setError("Failed to drop in from replay");
      return;
    }
    const payload: GamePayload = await res.json();
    onTakeoverGame(payload);
  };

  const downloadChronicleJson = () => {
    if (!currentChronicle || !activeReplay) return;
    const blob = new Blob([currentChronicle.chronicle_json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `oath_${activeReplay.replay_id}_chronicle_${currentChronicle.chronicle_number}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-bold text-amber-400">OATH-RS REPLAY LAB</span>
          <span className="text-xs text-slate-400">
            Simulate AI-vs-AI Chronicles • Inspect Decisions • Drop In & Play From Any Frame
          </span>
        </div>
        <button
          onClick={onBackToSetup}
          className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 cursor-pointer"
        >
          ← Back to Play / Scenario Stager
        </button>
      </header>

      <div className="grid grid-cols-12 gap-4 p-4 flex-1">
        {/* Left Sidebar: Simulator + Saved Replays (4 cols) */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 text-xs">
            <div className="text-sm font-bold text-amber-300">Simulate AI-vs-AI Match</div>

            <div className="grid grid-cols-3 gap-2">
              <label className="block">
                <span className="text-slate-400">Players</span>
                <select
                  value={numPlayers}
                  onChange={(e) => setNumPlayers(Number(e.target.value))}
                  className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1"
                >
                  {[2, 3, 4, 5, 6].map((n) => (
                    <option key={n} value={n}>
                      {n}p
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-slate-400">Chronicles</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={numChronicles}
                  onChange={(e) => setNumChronicles(Number(e.target.value))}
                  className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1"
                />
              </label>
              <label className="block">
                <span className="text-slate-400">Seed</span>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1"
                />
              </label>
            </div>

            <label className="block">
              <span className="text-slate-400">Starting Oath</span>
              <select
                value={oathGoal}
                onChange={(e) => setOathGoal(e.target.value)}
                className="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-2 py-1"
              >
                <option value="0">Supremacy</option>
                <option value="1">The People</option>
                <option value="2">Devotion</option>
                <option value="3">Sanctuary</option>
              </select>
            </label>

            <div className="space-y-1.5">
              {Array.from({ length: numPlayers }).map((_, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <span className="w-8 font-bold text-slate-300">P{idx}</span>
                  <select
                    value={seats[idx]}
                    onChange={(e) =>
                      setSeats((prev) => {
                        const n = [...prev];
                        n[idx] = e.target.value;
                        return n;
                      })
                    }
                    className="flex-1 bg-slate-800 border border-slate-700 rounded px-1.5 py-1"
                  >
                    {AI_SEAT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                  {seats[idx] === "lstm" && models.length > 0 && (
                    <select
                      value={seatCkpts[idx] ?? ""}
                      onChange={(e) =>
                        setSeatCkpts((prev) => {
                          const n = [...prev];
                          n[idx] = e.target.value || null;
                          return n;
                        })
                      }
                      className="max-w-[130px] bg-slate-950 border border-amber-500/40 rounded px-1.5 py-1 text-amber-200"
                    >
                      {models.map((m) => (
                        <option key={m.path} value={m.path}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              ))}
            </div>

            <textarea
              rows={2}
              placeholder="Optional: paste Chronicle JSON to start simulation from a prior world..."
              value={chronicleImport}
              onChange={(e) => setChronicleImport(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 font-mono text-[10px]"
            />

            <button
              onClick={runSimulation}
              disabled={simulating}
              className="w-full py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold cursor-pointer disabled:opacity-50"
            >
              {simulating ? "Simulating Chronicles..." : "Simulate & Watch Replay"}
            </button>
          </div>

          {/* Saved Replays */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 text-xs">
            <div className="font-bold text-slate-200">Saved Replays ({replays.length})</div>
            <div className="space-y-1.5 max-h-[280px] overflow-y-auto">
              {replays.length === 0 ? (
                <div className="text-slate-500 italic">No replays yet — run a simulation above.</div>
              ) : (
                replays.map((r) => (
                  <button
                    key={r.replay_id}
                    onClick={() => loadReplay(r.replay_id)}
                    className={`w-full text-left p-2 rounded-lg border cursor-pointer ${
                      activeReplay?.replay_id === r.replay_id
                        ? "bg-amber-500/20 border-amber-400"
                        : "bg-slate-800/60 border-slate-700 hover:bg-slate-800"
                    }`}
                  >
                    <div className="font-semibold text-slate-100 truncate">{r.name}</div>
                    <div className="text-[10px] text-slate-400">
                      {r.num_players}p • {r.num_chronicles} chronicle(s) • {r.replay_id}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: Replay Stage + Scrubber + Takeover (8 cols) */}
        <div className="col-span-12 lg:col-span-8 space-y-4">
          {error && (
            <div className="bg-red-900/70 border border-red-500/50 rounded-lg px-3 py-2 text-xs text-red-100">
              {error}
            </div>
          )}

          {!activeReplay || !currentChronicle || !currentFrame ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400 text-sm">
              Simulate a match on the left or pick a saved replay to inspect every move, watch bots negotiate & campaign, and drop in to play from any frame.
            </div>
          ) : (
            <>
              {/* Chronicle Switcher + Export + Drop-In Takeover Bar */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap gap-1.5">
                    {activeReplay.chronicles.map((c, idx) => (
                      <button
                        key={c.chronicle_number}
                        onClick={() => {
                          setPlaying(false);
                          setChronicleIdx(idx);
                          setFrameIdx(0);
                        }}
                        className={`px-2.5 py-1 rounded text-xs font-semibold cursor-pointer ${
                          chronicleIdx === idx
                            ? "bg-amber-500 text-slate-950"
                            : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                        }`}
                      >
                        Year {c.chronicle_number}: {c.oath_goal} (P{c.winner})
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={downloadChronicleJson}
                    className="text-xs px-2.5 py-1 rounded bg-emerald-900/60 hover:bg-emerald-800 border border-emerald-500/40 text-emerald-200 cursor-pointer"
                  >
                    Export Year {currentChronicle.chronicle_number} Chronicle JSON
                  </button>
                </div>

                {/* Scrubber & Playback Controls */}
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <button
                    onClick={() => {
                      setPlaying(false);
                      setFrameIdx(0);
                    }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 cursor-pointer"
                  >
                    ⏮
                  </button>
                  <button
                    onClick={() => {
                      setPlaying(false);
                      setFrameIdx((f) => Math.max(0, f - 1));
                    }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 cursor-pointer"
                  >
                    ◀
                  </button>
                  <button
                    onClick={() => setPlaying((p) => !p)}
                    className="px-3 py-1 rounded bg-amber-500 text-slate-950 font-bold cursor-pointer"
                  >
                    {playing ? "Pause" : "Play"}
                  </button>
                  <button
                    onClick={() => {
                      setPlaying(false);
                      setFrameIdx((f) => Math.min(currentChronicle.frames.length - 1, f + 1));
                    }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 cursor-pointer"
                  >
                    ▶
                  </button>
                  <input
                    type="range"
                    min={0}
                    max={Math.max(0, currentChronicle.frames.length - 1)}
                    value={frameIdx}
                    onChange={(e) => {
                      setPlaying(false);
                      setFrameIdx(Number(e.target.value));
                    }}
                    className="flex-1 accent-amber-500"
                  />
                  <span className="font-mono text-slate-300 w-24 text-right">
                    {frameIdx + 1} / {currentChronicle.frames.length}
                  </span>
                  <select
                    value={speedMs}
                    onChange={(e) => setSpeedMs(Number(e.target.value))}
                    className="bg-slate-800 border border-slate-700 rounded px-1.5 py-1"
                  >
                    <option value={800}>1×</option>
                    <option value={350}>2×</option>
                    <option value={120}>5×</option>
                  </select>
                </div>

                {/* Current Move + Drop-In Takeover */}
                <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-xs">
                  <div>
                    <span className="text-amber-400 font-bold">
                      {currentFrame.actor !== null ? `P${currentFrame.actor}` : "Setup"}
                    </span>{" "}
                    <span className="text-slate-200">{currentFrame.description}</span>
                    <span className="ml-2 text-slate-400">
                      (Round {currentFrame.state.round_number}/8 • Oath: {currentFrame.state.oath_goal})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={takeoverSeat}
                      onChange={(e) => setTakeoverSeat(Number(e.target.value))}
                      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
                    >
                      {Array.from({ length: activeReplay.num_players }).map((_, i) => (
                        <option key={i} value={i}>
                          Take over P{i} ({currentFrame.state.players[i]?.role})
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleTakeover}
                      className="px-3 py-1 rounded bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold cursor-pointer"
                    >
                      Drop In & Play Here
                    </button>
                  </div>
                </div>
              </div>

              {/* Compact Board View of Current Frame */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {currentFrame.state.sites.map((s, idx) => (
                  <div
                    key={idx}
                    className={`rounded-lg border p-2 text-xs ${
                      s.is_faceup
                        ? "bg-slate-900 border-slate-700"
                        : "bg-slate-950 border-slate-800 opacity-70"
                    }`}
                  >
                    <div className="flex justify-between font-semibold">
                      <span className="truncate">
                        {s.is_faceup ? s.site_meta?.name ?? `Site ${idx}` : `Facedown #${idx}`}
                      </span>
                      <span className="text-slate-500 text-[10px]">{s.region}</span>
                    </div>
                    {s.is_faceup && (
                      <div className="text-[11px] text-amber-300 mt-0.5">
                        {s.ruling_player !== null ? `P${s.ruling_player} (${s.warbands}wb)` : "Bandits"} • R:{s.relics.length}
                      </div>
                    )}
                    <div className="mt-1 space-y-0.5">
                      {s.is_faceup &&
                        s.card_metas.slice(0, s.capacity).map((cm, sl) =>
                          cm ? (
                            <div key={sl} className="flex items-center gap-1 text-[10px] truncate">
                              <span className={`w-1.5 h-1.5 rounded-full ${SUIT_COLORS[cm.suit] || SUIT_COLORS.None}`} />
                              <span className="truncate">{cm.name}</span>
                            </div>
                          ) : null
                        )}
                    </div>
                    <div className="flex gap-1 mt-1">
                      {currentFrame.state.players
                        .slice(0, currentFrame.state.num_players)
                        .map((p, pi) =>
                          p.pawn_site === idx ? (
                            <span
                              key={pi}
                              className={`text-[9px] font-bold px-1 rounded ${PLAYER_COLORS[pi % PLAYER_COLORS.length]}`}
                            >
                              P{pi}
                            </span>
                          ) : null
                        )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Players + AI Inspector + Talk */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-1.5">
                  <div className="font-semibold text-slate-300">Players</div>
                  {currentFrame.state.players
                    .slice(0, currentFrame.state.num_players)
                    .map((p, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between bg-slate-950/70 rounded px-2 py-1"
                      >
                        <span className="font-bold">
                          P{idx} ({p.role}) [{activeReplay.seats[idx]}]
                        </span>
                        <span className="text-slate-300">
                          Sup:{p.supply} Fav:{p.favor} Sec:{p.secrets_faceup} WB:{p.warbands_board} Rel:{p.relics.length}
                        </span>
                      </div>
                    ))}
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
                  <div className="font-semibold text-sky-400">
                    AI Inspector{" "}
                    {currentFrame.ai_inspector ? `(${currentFrame.ai_inspector.agent})` : ""}
                  </div>
                  {currentFrame.ai_inspector ? (
                    <div className="space-y-1">
                      {currentFrame.ai_inspector.top_actions.map((ta) => (
                        <div key={ta.action_id} className="flex items-center gap-2">
                          <span className="w-11 text-right font-mono text-amber-300">
                            {(ta.prob * 100).toFixed(1)}%
                          </span>
                          <span className="truncate text-slate-200">{ta.description}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-500 italic">No neural/MCTS policy data on this step.</div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
