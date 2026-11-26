import { useState } from "react";
import type { GamePayload, LegalAction, SiteState } from "../types/rustGame";

const SUIT_NAMES = ["Discord", "Arcane", "Order", "Hearth", "Beast", "Nomad"];
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
  payload: GamePayload;
  loading: boolean;
  onAction: (actionId: number) => void;
  onNewGame: () => void;
}

function decisionLabel(decision: string | Record<string, unknown>): string {
  if (typeof decision === "string") return decision;
  const key = Object.keys(decision)[0];
  return key ?? "Turn";
}

export default function RustGameBoard({ payload, loading, onAction, onNewGame }: Props) {
  const { state, seats, acting_player, is_human_turn, legal_actions, action_log, ai_inspector } =
    payload;
  const [showInspector, setShowInspector] = useState(true);
  const [activeTab, setActiveTab] = useState<"actions" | "talk" | "log">("actions");

  const groupedActions: Record<string, LegalAction[]> = {};
  for (const act of legal_actions) {
    if (!groupedActions[act.category]) groupedActions[act.category] = [];
    groupedActions[act.category].push(act);
  }

  const dpName = decisionLabel(state.decision);
  const isDealActive = state.deal !== null;
  const talkActions = groupedActions["TALK"] || [];
  const dealActions = groupedActions["DEAL"] || [];
  const mainCategories = Object.keys(groupedActions).filter((c) => c !== "TALK");

  const regions: { name: string; sites: { s: SiteState; idx: number }[] }[] = [
    { name: "Cradle", sites: [0, 1].map((idx) => ({ s: state.sites[idx], idx })) },
    { name: "Provinces", sites: [2, 3, 4].map((idx) => ({ s: state.sites[idx], idx })) },
    { name: "Hinterland", sites: [5, 6, 7].map((idx) => ({ s: state.sites[idx], idx })) },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Banner Bar */}
      <header className="bg-slate-900 border-b border-slate-800 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4 text-sm">
          <span className="font-bold text-amber-400">OATH-RS</span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
            Round {state.round_number}/8
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
            Oath: <b className="text-amber-300">{state.oath_goal}</b>
          </span>
          <span className="text-slate-300">
            Oathkeeper:{" "}
            <b>
              {state.oathkeeper_holder !== null ? `P${state.oathkeeper_holder}` : "None"} (
              {state.oathkeeper_side})
            </b>
          </span>
          <span className="text-slate-300">
            PF:{" "}
            <b>
              {state.peoples_favor_holder !== null ? `P${state.peoples_favor_holder}` : "—"} (
              {state.peoples_favor_tokens}
              {state.peoples_favor_is_mob ? " MOB" : ""})
            </b>
          </span>
          <span className="text-slate-300">
            DS:{" "}
            <b>
              {state.darkest_secret_holder !== null ? `P${state.darkest_secret_holder}` : "—"} (
              {state.darkest_secret_tokens})
            </b>
          </span>
          <span className="text-slate-400 text-xs">
            Visions: {state.visions_drawn}/5 • Deck: {state.world_deck.length} • Secrets Bank:{" "}
            {state.shared_secrets}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 mr-2">
            {state.favor_banks.map((cnt, i) => (
              <span
                key={i}
                title={`${SUIT_NAMES[i]} Favor Bank`}
                className="flex items-center gap-1 text-xs bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700"
              >
                <span className={`w-2 h-2 rounded-full ${SUIT_COLORS[SUIT_NAMES[i]]}`} />
                {cnt}
              </span>
            ))}
          </div>
          <button
            onClick={() => setShowInspector((v) => !v)}
            className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 cursor-pointer"
          >
            {showInspector ? "Hide AI Inspector" : "Show AI Inspector"}
          </button>
          <button
            onClick={async () => {
              const res = await fetch(`/api/games/${payload.game_id}/chronicle/export`);
              if (!res.ok) return;
              const d = await res.json();
              const blob = new Blob([d.chronicle_json], { type: "application/json" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `oath_chronicle_${payload.game_id}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="text-xs px-2.5 py-1 rounded bg-emerald-900/60 hover:bg-emerald-800 border border-emerald-500/40 text-emerald-200 cursor-pointer"
          >
            Export Chronicle
          </button>
          <button
            onClick={onNewGame}
            className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 cursor-pointer"
          >
            New Game
          </button>
        </div>
      </header>

      {/* Active Tribunal Contracts Strip */}
      {state.active_contracts.length > 0 && (
        <div className="bg-indigo-950/60 border-b border-indigo-500/30 px-4 py-1.5 text-xs flex items-center gap-3 flex-wrap">
          <span className="font-semibold text-indigo-300 uppercase">Active Tribunal Contracts:</span>
          {state.active_contracts.map((c, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded bg-indigo-900/70 border border-indigo-500/40 text-indigo-100"
            >
              P{c.party_a} ↔ P{c.party_b}: {JSON.stringify(c.clause)} [{JSON.stringify(c.enforcement)}]
            </span>
          ))}
        </div>
      )}

      {/* Main Layout */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-4">
        {/* Left: Map (7 cols) */}
        <div className="col-span-12 lg:col-span-7 space-y-4">
          {regions.map((reg) => (
            <div key={reg.name} className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                {reg.name}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                {reg.sites.map(({ s, idx }) => {
                  const pawnsHere = state.players
                    .slice(0, state.num_players)
                    .map((p, pi) => (p.pawn_site === idx ? pi : -1))
                    .filter((pi) => pi >= 0);
                  return (
                    <div
                      key={idx}
                      className={`rounded-lg border p-2.5 ${
                        s.is_faceup
                          ? "bg-slate-800/80 border-slate-700"
                          : "bg-slate-900 border-slate-800 opacity-75"
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="font-semibold text-slate-100">
                          {s.is_faceup ? s.site_meta?.name ?? `Site ${idx}` : `Facedown Site ${idx}`}
                        </span>
                        <span className="text-slate-400">
                          #{idx} {s.is_faceup ? `• Cap ${s.capacity}` : ""}
                        </span>
                      </div>

                      {s.is_faceup && (
                        <>
                          <div className="text-[11px] text-slate-400 flex items-center justify-between mb-1.5">
                            <span>
                              Ruler:{" "}
                              <b className="text-amber-300">
                                {s.ruling_player !== null
                                  ? `P${s.ruling_player} (${s.warbands} wb)`
                                  : "Bandits"}
                              </b>
                            </span>
                            <span>
                              F:{s.site_favor} S:{s.site_secrets} R:{s.relics.length}
                            </span>
                          </div>

                          <div className="space-y-1">
                            {Array.from({ length: s.capacity }).map((_, sl) => {
                              const cm = s.card_metas[sl];
                              return (
                                <div
                                  key={sl}
                                  title={cm?.text || ""}
                                  className="flex items-center justify-between text-xs bg-slate-900/80 rounded px-2 py-1 border border-slate-700/60"
                                >
                                  {cm ? (
                                    <span className="flex items-center gap-1.5 truncate">
                                      <span
                                        className={`w-2 h-2 rounded-full shrink-0 ${
                                          SUIT_COLORS[cm.suit] || SUIT_COLORS.None
                                        }`}
                                      />
                                      <span className="truncate">{cm.name}</span>
                                    </span>
                                  ) : (
                                    <span className="text-slate-600 italic">Empty slot</span>
                                  )}
                                  {cm && (s.card_favor[sl] > 0 || s.card_secrets[sl] > 0) && (
                                    <span className="text-[10px] text-amber-300 ml-1">
                                      {s.card_favor[sl] > 0 ? `F:${s.card_favor[sl]}` : ""}
                                      {s.card_secrets[sl] > 0 ? ` S:${s.card_secrets[sl]}` : ""}
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </>
                      )}

                      {pawnsHere.length > 0 && (
                        <div className="flex items-center gap-1 mt-2">
                          {pawnsHere.map((pi) => (
                            <span
                              key={pi}
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                                PLAYER_COLORS[pi % PLAYER_COLORS.length]
                              }`}
                            >
                              P{pi}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Interactive Binding Deal & Tribunal Contract Builder Panel */}
          {isDealActive && state.deal && (
            <div className="bg-amber-950/30 border-2 border-amber-500/50 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-amber-300 uppercase tracking-wide">
                  Binding Deal: {state.deal.kind} (Round {state.deal.round + 1}/3)
                </h2>
                <span className="text-xs text-slate-300">
                  Proposer: P{state.deal.proposer} → Responder: P{state.deal.responder}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-900/80 border border-slate-700 rounded-lg p-3">
                  <div className="font-semibold text-emerald-400 mb-1">
                    P{state.deal.proposer} Offers:
                  </div>
                  <div>Favor: {state.deal.offer.favor} • Secrets: {state.deal.offer.secrets}</div>
                  {state.deal.offer.reliquary_slot !== null && (
                    <div className="text-amber-300">
                      Reliquary Slot #{state.deal.offer.reliquary_slot}{" "}
                      {state.deal.allow_reliquary_peek ? "(Peek Allowed)" : "(Blind)"}
                    </div>
                  )}
                  {state.deal.offer.relics.length > 0 && (
                    <div>Relics: {state.deal.offer.relics.join(", ")}</div>
                  )}
                  {state.deal.offer.advisers.length > 0 && (
                    <div>Adviser slots: {state.deal.offer.advisers.join(", ")}</div>
                  )}
                  {state.deal.offer.sites.length > 0 && (
                    <div>Ruled sites: {state.deal.offer.sites.join(", ")}</div>
                  )}
                </div>

                <div className="bg-slate-900/80 border border-slate-700 rounded-lg p-3">
                  <div className="font-semibold text-sky-400 mb-1">
                    P{state.deal.proposer} Requests from P{state.deal.responder}:
                  </div>
                  <div>Favor: {state.deal.request.favor} • Secrets: {state.deal.request.secrets}</div>
                  {state.deal.request.relics.length > 0 && (
                    <div>Relics: {state.deal.request.relics.join(", ")}</div>
                  )}
                  {state.deal.request.advisers.length > 0 && (
                    <div>Adviser slots: {state.deal.request.advisers.join(", ")}</div>
                  )}
                  {state.deal.request.sites.length > 0 && (
                    <div>Ruled sites: {state.deal.request.sites.join(", ")}</div>
                  )}
                </div>
              </div>

              {state.deal.contracts.length > 0 && (
                <div className="text-xs bg-indigo-950/60 border border-indigo-500/40 rounded-lg p-2">
                  <div className="font-semibold text-indigo-300 mb-1">Attached Tribunal Contracts:</div>
                  {state.deal.contracts.map((c, i) => (
                    <div key={i}>
                      • {JSON.stringify(c.clause)} ({JSON.stringify(c.enforcement)})
                    </div>
                  ))}
                </div>
              )}

              {is_human_turn && dealActions.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {dealActions.map((a) => (
                    <button
                      key={a.action_id}
                      disabled={loading}
                      onClick={() => onAction(a.action_id)}
                      className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/40 border border-amber-400/40 text-xs text-amber-100 cursor-pointer"
                    >
                      {a.description}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Players + Dynamic Decision Drawer + Table Talk + AI Inspector (5 cols) */}
        <div className="col-span-12 lg:col-span-5 space-y-4">
          {/* Players List */}
          <div className="grid grid-cols-2 gap-2">
            {state.players.slice(0, state.num_players).map((p, idx) => {
              const active = acting_player === idx;
              return (
                <div
                  key={idx}
                  className={`rounded-xl border p-2.5 text-xs ${
                    active
                      ? "bg-slate-800 border-amber-400 ring-1 ring-amber-400/50"
                      : "bg-slate-900 border-slate-800"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold flex items-center gap-1.5">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          PLAYER_COLORS[idx % PLAYER_COLORS.length].split(" ")[0]
                        }`}
                      />
                      P{idx} ({p.role})
                    </span>
                    <span className="text-[10px] uppercase text-slate-400">{seats[idx]}</span>
                  </div>
                  <div className="text-slate-300 flex flex-wrap gap-x-2 gap-y-0.5">
                    <span>Sup:{p.supply}</span>
                    <span>Fav:{p.favor}</span>
                    <span>
                      Sec:{p.secrets_faceup}
                      {p.secrets_facedown > 0 ? `+${p.secrets_facedown}fd` : ""}
                    </span>
                    <span>
                      WB:{p.warbands_board}/{p.warbands_bank}
                    </span>
                    <span>Site:#{p.pawn_site}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {p.adviser_metas.map((am, sl) =>
                      am ? (
                        <span
                          key={sl}
                          title={p.adviser_faceup[sl] || seats[idx] === "human" ? am.text : "Facedown adviser"}
                          className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-700 text-[10px]"
                        >
                          {p.adviser_faceup[sl] || seats[idx] === "human" ? am.name : "Facedown"}
                        </span>
                      ) : null
                    )}
                    {p.relic_metas.map((rm, sl) =>
                      rm ? (
                        <span
                          key={`r-${sl}`}
                          title={rm.text}
                          className="px-1.5 py-0.5 rounded bg-amber-900/40 border border-amber-500/40 text-amber-200 text-[10px]"
                        >
                          ★ {rm.name}
                        </span>
                      ) : null
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Decision Drawer + Table Talk + Log Tabs */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2 bg-slate-900/90">
              <div className="flex gap-1.5">
                {(["actions", "talk", "log"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveTab(t)}
                    className={`px-2.5 py-1 rounded text-xs font-semibold uppercase cursor-pointer ${
                      activeTab === t
                        ? "bg-amber-500 text-slate-950"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {t === "actions"
                      ? `Decision: ${dpName}`
                      : t === "talk"
                      ? `Table Talk (${state.talk_log.length})`
                      : `Log (${action_log.length})`}
                  </button>
                ))}
              </div>
              <span className="text-xs text-slate-400">
                {state.is_game_over
                  ? `Winner: P${state.winner} (${state.win_type})`
                  : is_human_turn
                  ? `Your turn (P${acting_player})`
                  : `AI Thinking (P${acting_player})`}
              </span>
            </div>

            <div className="p-3 max-h-[380px] overflow-y-auto space-y-3">
              {activeTab === "actions" && (
                <>
                  {state.is_game_over ? (
                    <div className="text-center py-6 space-y-2">
                      <div className="text-xl font-bold text-amber-400">
                        Player {state.winner} Wins!
                      </div>
                      <div className="text-sm text-slate-300">Victory Type: {state.win_type}</div>
                      <button
                        onClick={onNewGame}
                        className="mt-2 px-4 py-2 rounded-lg bg-amber-500 text-slate-950 font-bold text-xs cursor-pointer"
                      >
                        Play Again
                      </button>
                    </div>
                  ) : is_human_turn ? (
                    mainCategories.map((cat) => (
                      <div key={cat}>
                        <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">
                          {cat}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {groupedActions[cat].map((a) => (
                            <button
                              key={a.action_id}
                              disabled={loading}
                              onClick={() => onAction(a.action_id)}
                              className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-amber-500 hover:text-slate-950 border border-slate-700 text-xs transition cursor-pointer disabled:opacity-50"
                            >
                              {a.description}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-slate-400 py-4 text-center">
                      Waiting for AI player P{acting_player}...
                    </div>
                  )}
                </>
              )}

              {activeTab === "talk" && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    {state.talk_log.length === 0 ? (
                      <div className="text-xs text-slate-500 italic">No table talk yet.</div>
                    ) : (
                      state.talk_log.map((ev, i) => (
                        <div
                          key={i}
                          className="text-xs bg-slate-800/80 border border-slate-700/60 rounded px-2.5 py-1.5"
                        >
                          <span className="font-bold text-amber-300">P{ev.sender}</span>{" "}
                          <span className="text-slate-400">(R{ev.round})</span>:{" "}
                          <span>{ev.intent}</span>
                          {ev.target !== null && <span> → P{ev.target}</span>}
                          {ev.suit && <span> [{ev.suit}]</span>}
                          {ev.shown_card !== null && (
                            <span className="ml-1 text-emerald-400 font-semibold">
                              (Verified Card #{ev.shown_card})
                            </span>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                  {is_human_turn && talkActions.length > 0 && (
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-semibold mb-1">
                        Quick Table Talk & Show Adviser
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {talkActions.map((a) => (
                          <button
                            key={a.action_id}
                            disabled={loading}
                            onClick={() => onAction(a.action_id)}
                            className="px-2 py-1 rounded bg-sky-900/50 hover:bg-sky-700 border border-sky-500/40 text-xs text-sky-100 cursor-pointer"
                          >
                            {a.description}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === "log" && (
                <div className="space-y-1 text-xs">
                  {action_log.map((e, i) => (
                    <div key={i} className="text-slate-300">
                      <span className="font-semibold text-amber-400">
                        [P{e.player} {e.seat}]
                      </span>{" "}
                      {e.description}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* AI Policy / Value Inspector */}
          {showInspector && ai_inspector && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-sky-400">
                  AI Inspector — P{ai_inspector.player} ({ai_inspector.agent})
                </span>
                <span className="text-slate-400">
                  Win Est: {ai_inspector.win_probs.map((v, i) => `P${i}:${(v * 100).toFixed(0)}%`).join(" ")}
                </span>
              </div>
              <div className="space-y-1">
                {ai_inspector.top_actions.map((ta) => (
                  <div key={ta.action_id} className="flex items-center gap-2">
                    <div className="w-12 text-right font-mono text-amber-300">
                      {(ta.prob * 100).toFixed(1)}%
                    </div>
                    <div className="flex-1 bg-slate-800 rounded h-2 overflow-hidden">
                      <div
                        className="bg-amber-400 h-full"
                        style={{ width: `${Math.min(100, ta.prob * 100)}%` }}
                      />
                    </div>
                    <div className="truncate max-w-[200px] text-slate-300">{ta.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
