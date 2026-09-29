import { QueryClient } from "@tanstack/react-query";

/**
 * Server-owned data (lists the API is the source of truth for) is cached here;
 * `stores/` keeps only UI state and what the user is typing.
 *
 * Defaults match what the hand-written loaders did: no automatic retry (a 401
 * or a validation error will not get better, and callers already surface the
 * failure once), and no refetch on window focus (the pages poll on their own
 * schedule where that matters).
 *
 * Cleared on logout and on any identity change (App.tsx `clearUserState`),
 * for the reason the Zustand stores are reset: the next person on a shared
 * browser must not see the previous one's data while the first fetch lands.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, refetchOnWindowFocus: false, staleTime: 0 },
  },
});
