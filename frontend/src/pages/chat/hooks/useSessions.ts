import { useQuery } from "@tanstack/react-query";
import { appApi } from "@/lib/api";

export const SESSIONS_QUERY_KEY = ["sessions"] as const;

export function fetchSessions() {
  return appApi.sessions();
}

/** The sessions already in the cache, without fetching: for views that show them if the chat page loaded some. */
export function useCachedSessions() {
  const query = useQuery({ queryKey: SESSIONS_QUERY_KEY, queryFn: fetchSessions, enabled: false });
  return query.data ?? [];
}

/** The caller's sessions, newest activity first as the API returns them. `sessionLoading` is true only until the first answer. */
export function useSessions() {
  const query = useQuery({ queryKey: SESSIONS_QUERY_KEY, queryFn: fetchSessions });
  return { sessions: query.data ?? [], sessionLoading: query.isPending };
}
