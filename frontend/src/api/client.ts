import type { CreateGameRequest, GameResponse } from "../types/game";

const BASE = "/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export async function createGame(config: CreateGameRequest): Promise<GameResponse> {
  return request<GameResponse>("/games", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export async function getState(gameId: string): Promise<GameResponse> {
  return request<GameResponse>(`/games/${gameId}/state`);
}

export async function submitAction(gameId: string, actionId: number): Promise<GameResponse> {
  return request<GameResponse>(`/games/${gameId}/action`, {
    method: "POST",
    body: JSON.stringify({ action_id: actionId }),
  });
}
