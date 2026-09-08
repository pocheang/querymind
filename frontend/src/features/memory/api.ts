import { authRequest } from "@/lib/api-client";

/**
 * The record of what this system remembers about the signed-in person.
 *
 * Deliberately not the session endpoints (`/sessions/{id}/memories/long`).
 * Those return a working set -- the handful of memories one conversation would
 * be given, capped at five and ordered per session -- which is the wrong thing
 * to put behind a control labelled "what do you remember about me".
 */

/** Why the resolver kept this. An unknown value is a row from an older shape. */
export type MemoryKind = "preference" | "stable_fact" | "task" | "explicit_remember" | "";

export type StoredMemory = {
  memory_id: string;
  kind: MemoryKind;
  content: string;
  score: number;
  /** False once the TTL has passed: still stored, no longer reaching the model. */
  active: boolean;
  created_at: string | null;
  updated_at: string | null;
  expires_at: string | null;
  source_session_id: string | null;
};

const BASE = "/api/v1/memories";

export async function listMemories(signal?: AbortSignal): Promise<readonly StoredMemory[]> {
  const response = await authRequest<{ memories: StoredMemory[]; total: number }>(BASE, { signal });
  return response.memories ?? [];
}

export function forgetMemory(memoryId: string): Promise<{ ok: boolean; memory_id: string }> {
  return authRequest<{ ok: boolean; memory_id: string }>(`${BASE}/${encodeURIComponent(memoryId)}`, {
    method: "DELETE",
  });
}

export function forgetAllMemories(): Promise<{ ok: boolean; forgotten: number }> {
  return authRequest<{ ok: boolean; forgotten: number }>(BASE, { method: "DELETE" });
}
