import { useState, useCallback, useEffect, useRef } from "react";
import type { GameResponse, CreateGameRequest, ActionHighlights, ActionLogEntry } from "../types/game";
import { AI_ACTION_DELAY_MS } from "../types/game";
import { createGame, submitAction } from "../api/client";

export function useGame() {
  const [gameData, setGameData] = useState<GameResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Animation state
  const [aiQueue, setAiQueue] = useState<ActionLogEntry[]>([]);
  const [aiStep, setAiStep] = useState(-1); // -1 = not animating
  const [activeHighlights, setActiveHighlights] = useState<ActionHighlights | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isAnimating = aiStep >= 0;

  // How many AI actions from the current batch are visible in the log
  const visibleAiActionCount = isAnimating ? aiStep + 1 : aiQueue.length;

  // Start animation when new AI actions arrive
  const startAnimation = useCallback((actions: ActionLogEntry[]) => {
    // Filter out comm signals — they're no-ops and would clutter the animation
    const meaningful = actions.filter(
      (a) => !a.description.startsWith("Send signal") && !a.description.startsWith("Signal target")
    );
    if (meaningful.length === 0) {
      setAiQueue([]);
      setAiStep(-1);
      setActiveHighlights(null);
      return;
    }
    setAiQueue(meaningful);
    setAiStep(0);
    setActiveHighlights(meaningful[0]?.highlights || null);
  }, []);

  // Timer-driven animation: advance one step every AI_ACTION_DELAY_MS
  useEffect(() => {
    if (aiStep < 0 || aiStep >= aiQueue.length) return;

    timerRef.current = setTimeout(() => {
      const next = aiStep + 1;
      if (next < aiQueue.length) {
        setAiStep(next);
        setActiveHighlights(aiQueue[next]?.highlights || null);
      } else {
        // Done animating
        setAiStep(-1);
        setActiveHighlights(null);
      }
    }, AI_ACTION_DELAY_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [aiStep, aiQueue]);

  const handleResponse = useCallback((data: GameResponse) => {
    setGameData(data);
    if (data.ai_actions.length > 0) {
      startAnimation(data.ai_actions);
    } else {
      setAiQueue([]);
      setAiStep(-1);
      setActiveHighlights(null);
    }
  }, [startAnimation]);

  const startGame = useCallback(async (config: CreateGameRequest) => {
    setLoading(true);
    setError(null);
    try {
      const data = await createGame(config);
      handleResponse(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create game");
    } finally {
      setLoading(false);
    }
  }, [handleResponse]);

  const takeAction = useCallback(async (actionId: number) => {
    if (!gameData || isAnimating) return;
    setLoading(true);
    setError(null);
    try {
      const data = await submitAction(gameData.game_id, actionId);
      handleResponse(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit action");
    } finally {
      setLoading(false);
    }
  }, [gameData, isAnimating, handleResponse]);

  const resetGame = useCallback(() => {
    setGameData(null);
    setError(null);
    setAiQueue([]);
    setAiStep(-1);
    setActiveHighlights(null);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  return {
    gameData,
    loading,
    error,
    startGame,
    takeAction,
    resetGame,
    activeHighlights,
    isAnimating,
    visibleAiActionCount,
    animatingAction: isAnimating ? aiQueue[aiStep] : null,
  };
}
