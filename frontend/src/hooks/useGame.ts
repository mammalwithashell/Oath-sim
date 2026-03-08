import { useState, useCallback } from "react";
import type { GameResponse, CreateGameRequest } from "../types/game";
import { createGame, submitAction } from "../api/client";

export function useGame() {
  const [gameData, setGameData] = useState<GameResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startGame = useCallback(async (config: CreateGameRequest) => {
    setLoading(true);
    setError(null);
    try {
      const data = await createGame(config);
      setGameData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create game");
    } finally {
      setLoading(false);
    }
  }, []);

  const takeAction = useCallback(async (actionId: number) => {
    if (!gameData) return;
    setLoading(true);
    setError(null);
    try {
      const data = await submitAction(gameData.game_id, actionId);
      setGameData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit action");
    } finally {
      setLoading(false);
    }
  }, [gameData]);

  const resetGame = useCallback(() => {
    setGameData(null);
    setError(null);
  }, []);

  return { gameData, loading, error, startGame, takeAction, resetGame };
}
