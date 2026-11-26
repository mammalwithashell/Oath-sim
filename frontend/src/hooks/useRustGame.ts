import { useCallback, useEffect, useRef, useState } from "react";
import type { CreateGameConfig, GamePayload } from "../types/rustGame";

export function useRustGame() {
  const [payload, setPayload] = useState<GamePayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => closeWs, [closeWs]);

  const connectWs = useCallback(
    (gameId: string) => {
      closeWs();
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/games/${gameId}`);
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.error) {
            setError(data.error);
          } else {
            setPayload(data);
            setError(null);
          }
        } catch {
          // ignore malformed frame
        }
        setLoading(false);
      };
      ws.onerror = () => {
        // REST fallback remains available
      };
      wsRef.current = ws;
    },
    [closeWs]
  );

  const startGame = useCallback(
    async (cfg: CreateGameConfig) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/games", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cfg),
        });
        if (!res.ok) throw new Error(await res.text());
        const data: GamePayload = await res.json();
        setPayload(data);
        connectWs(data.game_id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to start game");
      } finally {
        setLoading(false);
      }
    },
    [connectWs]
  );

  const sendAction = useCallback(
    async (actionId: number) => {
      if (!payload) return;
      setLoading(true);
      setError(null);
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action_id: actionId }));
        return;
      }
      try {
        const res = await fetch(`/api/games/${payload.game_id}/action`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action_id: actionId }),
        });
        if (!res.ok) throw new Error(await res.text());
        const data: GamePayload = await res.json();
        setPayload(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Action failed");
      } finally {
        setLoading(false);
      }
    },
    [payload]
  );

  const loadPayload = useCallback(
    (data: GamePayload) => {
      setPayload(data);
      setError(null);
      connectWs(data.game_id);
    },
    [connectWs]
  );

  const resetGame = useCallback(() => {
    closeWs();
    setPayload(null);
    setError(null);
  }, [closeWs]);

  return { payload, loading, error, startGame, sendAction, loadPayload, resetGame };
}
