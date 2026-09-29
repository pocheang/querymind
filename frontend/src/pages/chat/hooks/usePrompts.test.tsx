// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const prompts = vi.fn();

vi.mock("@/lib/api", () => ({ appApi: { prompts: (...args: unknown[]) => prompts(...args) } }));

const { queryClient } = await import("@/lib/queryClient");
const { usePrompts, PROMPTS_QUERY_KEY } = await import("./usePrompts");

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

describe("usePrompts", () => {
  beforeEach(() => {
    prompts.mockReset();
    queryClient.clear();
  });
  afterEach(cleanup);

  it("is loading until the first answer, then serves the list", async () => {
    prompts.mockResolvedValue([{ prompt_id: "p1", title: "t" }]);

    const { result } = renderHook(() => usePrompts(), { wrapper });

    expect(result.current.promptsLoading).toBe(true);
    expect(result.current.prompts).toEqual([]);
    await waitFor(() => expect(result.current.promptsLoading).toBe(false));
    expect(result.current.prompts).toHaveLength(1);
  });

  it("does not show a refresh as loading", async () => {
    prompts.mockResolvedValue([{ prompt_id: "p1", title: "t" }]);
    const { result } = renderHook(() => usePrompts(), { wrapper });
    await waitFor(() => expect(result.current.promptsLoading).toBe(false));

    prompts.mockResolvedValue([
      { prompt_id: "p1", title: "t" },
      { prompt_id: "p2", title: "u" },
    ]);
    await queryClient.fetchQuery({ queryKey: PROMPTS_QUERY_KEY, queryFn: () => prompts(), staleTime: 0 });

    await waitFor(() => expect(result.current.prompts).toHaveLength(2));
    expect(result.current.promptsLoading).toBe(false);
  });

  it("forgets the previous user's list when the cache is cleared (logout)", async () => {
    prompts.mockResolvedValue([{ prompt_id: "p1", title: "alice's" }]);
    const { result } = renderHook(() => usePrompts(), { wrapper });
    await waitFor(() => expect(result.current.prompts).toHaveLength(1));

    queryClient.clear();

    expect(queryClient.getQueryData(PROMPTS_QUERY_KEY)).toBeUndefined();
  });
});
