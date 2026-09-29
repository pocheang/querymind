// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const sessions = vi.fn();
const documents = vi.fn();

vi.mock("@/lib/api", () => ({
  appApi: {
    sessions: (...args: unknown[]) => sessions(...args),
    documents: (...args: unknown[]) => documents(...args),
  },
}));

const { queryClient } = await import("@/lib/queryClient");
const { useSessions, useCachedSessions, SESSIONS_QUERY_KEY } = await import("./useSessions");
const { useDocuments, DOCUMENTS_QUERY_KEY } = await import("./useDocuments");

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("server-owned lists", () => {
  beforeEach(() => {
    sessions.mockReset();
    documents.mockReset();
    queryClient.clear();
  });
  afterEach(cleanup);

  it("sessions load once and are shared by every reader", async () => {
    sessions.mockResolvedValue([{ session_id: "s1", title: "a" }]);

    const a = renderHook(() => useSessions(), { wrapper });
    const b = renderHook(() => useSessions(), { wrapper });

    expect(a.result.current.sessionLoading).toBe(true);
    await waitFor(() => expect(a.result.current.sessions).toHaveLength(1));
    await waitFor(() => expect(b.result.current.sessions).toHaveLength(1));
    expect(sessions).toHaveBeenCalledTimes(1);
  });

  it("documents load and a refresh is not shown as loading", async () => {
    documents.mockResolvedValue([{ document_id: "d1" }]);
    const { result } = renderHook(() => useDocuments(), { wrapper });
    await waitFor(() => expect(result.current.docsLoading).toBe(false));

    documents.mockResolvedValue([{ document_id: "d1" }, { document_id: "d2" }]);
    await queryClient.fetchQuery({ queryKey: DOCUMENTS_QUERY_KEY, queryFn: () => documents(), staleTime: 0 });

    await waitFor(() => expect(result.current.documents).toHaveLength(2));
    expect(result.current.docsLoading).toBe(false);
  });

  it("the cached reader never fetches but follows what the chat page loads", async () => {
    const { result } = renderHook(() => useCachedSessions(), { wrapper });
    expect(result.current).toEqual([]);
    expect(sessions).not.toHaveBeenCalled();

    queryClient.setQueryData(SESSIONS_QUERY_KEY, [{ session_id: "s1" }]);

    await waitFor(() => expect(result.current).toHaveLength(1));
    expect(sessions).not.toHaveBeenCalled();
  });
});
