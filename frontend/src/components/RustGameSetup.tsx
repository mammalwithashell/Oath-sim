import { useEffect, useState } from "react";
import type { CatalogData, CreateGameConfig, ModelInfo } from "../types/rustGame";

const SEAT_OPTIONS = [
  { value: "human", label: "Human" },
  { value: "lstm", label: "LSTM (PyTorch)" },
  { value: "mcts", label: "IS-MCTS (Rust)" },
  { value: "heuristic", label: "Role-Aware Bot (Rust)" },
  { value: "random", label: "Random" },
];

const OATH_OPTIONS = [
  { value: "", label: "Random Oath" },
  { value: "0", label: "Supremacy (Most Sites)" },
  { value: "1", label: "The People (People's Favor)" },
  { value: "2", label: "Devotion (Darkest Secret)" },
  { value: "3", label: "Sanctuary (Most Relics & Banners)" },
];

const DEFAULT_SITES = [251, 249, 253, 246, 250, 248, 259, 254];

interface Props {
  onStart: (cfg: CreateGameConfig) => void;
  onOpenReplays: () => void;
  loading: boolean;
}

export default function RustGameSetup({ onStart, onOpenReplays, loading }: Props) {
  const [numPlayers, setNumPlayers] = useState(4);
  const [seats, setSeats] = useState<string[]>([
    "lstm",
    "human",
    "lstm",
    "heuristic",
    "heuristic",
    "heuristic",
  ]);
  const [seatCheckpoints, setSeatCheckpoints] = useState<(string | null)[]>([
    null,
    null,
    null,
    null,
    null,
    null,
  ]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [catalog, setCatalog] = useState<CatalogData>({ sites: [], relics: [] });

  const [seed, setSeed] = useState(42);
  const [firstGame, setFirstGame] = useState(true);
  const [chronicle, setChronicle] = useState(true);
  const [oathGoal, setOathGoal] = useState<string>("0");

  // Scenario Stager & Chronicle Import
  const [showStager, setShowStager] = useState(false);
  const [useCustomSites, setUseCustomSites] = useState(false);
  const [stagedSites, setStagedSites] = useState<number[]>(DEFAULT_SITES);
  const [stagedReliquary, setStagedReliquary] = useState<number[]>([]);
  const [stagedChancellorRelics, setStagedChancellorRelics] = useState<number[]>([]);
  const [chronicleJson, setChronicleJson] = useState<string>("");

  useEffect(() => {
    fetch("/api/models")
      .then((r) => r.json())
      .then((d) => {
        const list: ModelInfo[] = d.models || [];
        setModels(list);
        if (list.length > 0) {
          const def = list.find((m) => m.name.includes("best"))?.path ?? list[0].path;
          setSeatCheckpoints((prev) => prev.map((v) => v ?? def));
        }
      })
      .catch(() => {});
    fetch("/api/catalog")
      .then((r) => r.json())
      .then((d) => setCatalog(d))
      .catch(() => {});
  }, []);

  const toggleRelic = (list: number[], setList: (v: number[]) => void, id: number, max: number) => {
    if (list.includes(id)) {
      setList(list.filter((x) => x !== id));
    } else if (list.length < max) {
      setList([...list, id]);
    }
  };

  const handleFileImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    file.text().then((txt) => setChronicleJson(txt));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStart({
      num_players: numPlayers,
      seats: seats.slice(0, numPlayers),
      seat_checkpoints: seatCheckpoints.slice(0, numPlayers),
      seed,
      first_game: firstGame,
      oath_goal: oathGoal === "" ? null : Number(oathGoal),
      chronicle_enabled: chronicle,
      staged_sites: useCustomSites ? stagedSites : null,
      staged_reliquary: stagedReliquary.length > 0 ? stagedReliquary : null,
      staged_chancellor_relics: stagedChancellorRelics.length > 0 ? stagedChancellorRelics : null,
      chronicle_json: chronicleJson.trim() ? chronicleJson.trim() : null,
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl bg-slate-900 border border-amber-500/30 rounded-2xl p-8 shadow-2xl space-y-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-amber-400 font-semibold">
              Oath-sim Rust Engine • 259 Cards • Deals & Table Talk
            </div>
            <h1 className="text-3xl font-bold mt-1 text-slate-50">
              Oath: Chronicles of Empire & Exile
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Play against trained PyTorch LSTM checkpoints, Rust IS-MCTS, or Role-Aware Bots — or stage custom scenarios & Chronicles.
            </p>
          </div>
          <button
            type="button"
            onClick={onOpenReplays}
            className="shrink-0 px-3.5 py-2 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-400/40 text-sky-200 text-xs font-semibold cursor-pointer"
          >
            Simulate & Replay Viewer →
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs text-slate-400 uppercase">Players (2–6)</span>
            <select
              value={numPlayers}
              onChange={(e) => setNumPlayers(Number(e.target.value))}
              className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            >
              {[2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>
                  {n} Players
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs text-slate-400 uppercase">Starting Oath Goal</span>
            <select
              value={oathGoal}
              onChange={(e) => setOathGoal(e.target.value)}
              className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            >
              {OATH_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="space-y-2">
          <div className="text-xs text-slate-400 uppercase">Seat & Model Assignments</div>
          {Array.from({ length: numPlayers }).map((_, idx) => (
            <div
              key={idx}
              className="flex flex-wrap items-center justify-between gap-2 bg-slate-800/70 border border-slate-700/60 rounded-lg px-3 py-2"
            >
              <span className="text-sm font-medium">
                Player {idx}{" "}
                <span className={idx === 0 ? "text-amber-400 text-xs" : "text-slate-400 text-xs"}>
                  ({idx === 0 ? "Chancellor" : "Exile"})
                </span>
              </span>
              <div className="flex items-center gap-2">
                <select
                  value={seats[idx]}
                  onChange={(e) =>
                    setSeats((prev) => {
                      const next = [...prev];
                      next[idx] = e.target.value;
                      return next;
                    })
                  }
                  className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-sm"
                >
                  {SEAT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {seats[idx] === "lstm" && models.length > 0 && (
                  <select
                    value={seatCheckpoints[idx] ?? ""}
                    onChange={(e) =>
                      setSeatCheckpoints((prev) => {
                        const next = [...prev];
                        next[idx] = e.target.value || null;
                        return next;
                      })
                    }
                    className="bg-slate-900 border border-amber-500/40 rounded px-2 py-1 text-xs text-amber-200 max-w-[190px]"
                  >
                    {models.map((m) => (
                      <option key={m.path} value={m.path}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-4 items-center">
          <label className="block">
            <span className="text-xs text-slate-400 uppercase">Seed</span>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer pt-4">
            <input
              type="checkbox"
              checked={firstGame}
              onChange={(e) => setFirstGame(e.target.checked)}
              className="accent-amber-500"
            />
            First-game map
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer pt-4">
            <input
              type="checkbox"
              checked={chronicle}
              onChange={(e) => setChronicle(e.target.checked)}
              className="accent-amber-500"
            />
            Chronicle mode
          </label>
        </div>

        {/* Collapsible Scenario Stager & Chronicle Import */}
        <div className="border border-slate-700/80 rounded-xl overflow-hidden">
          <button
            type="button"
            onClick={() => setShowStager((v) => !v)}
            className="w-full px-4 py-2.5 bg-slate-800/80 hover:bg-slate-800 flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-amber-300 cursor-pointer"
          >
            <span>Scenario Stager & Chronicle Import (Sites, Relics, Prior Chronicle)</span>
            <span>{showStager ? "▲" : "▼"}</span>
          </button>

          {showStager && (
            <div className="p-4 space-y-4 bg-slate-950/60 text-xs">
              {/* Chronicle Import */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-semibold">Import Chronicle JSON (optional)</span>
                  <input type="file" accept=".json" onChange={handleFileImport} className="text-[11px] text-slate-400" />
                </div>
                <textarea
                  rows={2}
                  placeholder="Paste exported ChronicleState JSON here to continue an existing world..."
                  value={chronicleJson}
                  onChange={(e) => setChronicleJson(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 font-mono text-[11px]"
                />
              </div>

              {/* Custom Sites */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 font-semibold text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useCustomSites}
                    onChange={(e) => setUseCustomSites(e.target.checked)}
                    className="accent-amber-500"
                  />
                  Stage Custom Map Sites (0–1 Cradle, 2–4 Provinces, 5–7 Hinterland)
                </label>
                {useCustomSites && catalog.sites.length > 0 && (
                  <div className="grid grid-cols-2 gap-2">
                    {stagedSites.map((sid, slot) => (
                      <div key={slot} className="flex items-center gap-2">
                        <span className="w-12 text-slate-400">Site #{slot}</span>
                        <select
                          value={sid}
                          onChange={(e) =>
                            setStagedSites((prev) => {
                              const next = [...prev];
                              next[slot] = Number(e.target.value);
                              return next;
                            })
                          }
                          className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1"
                        >
                          {catalog.sites.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Stage Chancellor's Reliquary */}
              {catalog.relics.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-slate-300 font-semibold">
                    Stage Imperial Reliquary Relics (pick up to 4: {stagedReliquary.length}/4)
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {catalog.relics.map((r) => {
                      const active = stagedReliquary.includes(r.id);
                      return (
                        <button
                          key={r.id}
                          type="button"
                          onClick={() => toggleRelic(stagedReliquary, setStagedReliquary, r.id, 4)}
                          className={`px-2 py-0.5 rounded border text-[11px] cursor-pointer ${
                            active
                              ? "bg-amber-500 text-slate-950 border-amber-400 font-semibold"
                              : "bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500"
                          }`}
                        >
                          {r.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Stage Chancellor's Held Relics */}
              {catalog.relics.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-slate-300 font-semibold">
                    Stage Chancellor Held Relics (+ Grand Scepter, up to 4: {stagedChancellorRelics.length}/4)
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {catalog.relics.map((r) => {
                      const active = stagedChancellorRelics.includes(r.id);
                      return (
                        <button
                          key={`ch-${r.id}`}
                          type="button"
                          onClick={() =>
                            toggleRelic(stagedChancellorRelics, setStagedChancellorRelics, r.id, 4)
                          }
                          className={`px-2 py-0.5 rounded border text-[11px] cursor-pointer ${
                            active
                              ? "bg-emerald-500 text-slate-950 border-emerald-400 font-semibold"
                              : "bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500"
                          }`}
                        >
                          {r.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm transition cursor-pointer disabled:opacity-50"
        >
          {loading ? "Starting Engine..." : "Launch Interactive Oath Game"}
        </button>
      </form>
    </div>
  );
}
