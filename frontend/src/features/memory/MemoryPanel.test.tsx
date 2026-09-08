// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MemoryPanel } from "@/features/memory/MemoryPanel";
import type { StoredMemory } from "@/features/memory/api";

/**
 * The panel is the only place anybody can see what this system has stored
 * about them, so the three things worth pinning are the three ways it could
 * quietly say something untrue:
 *
 * 1. showing fewer memories than are held -- the defect the whole feature
 *    exists to fix, since the session endpoint caps its list at five;
 * 2. hiding an expired one, which is still on disk and still deletable;
 * 3. rendering a failed request as an empty list, so "we hold nothing about
 *    you" and "we could not ask" look identical.
 *
 * Plus the one destructive control: deleting everything must ask first.
 */

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join(",")}` : key,
    i18n: { language: "en" },
  }),
}));

const listMemories = vi.fn();
const forgetMemory = vi.fn();
const forgetAllMemories = vi.fn();
vi.mock("@/features/memory/api", () => ({
  listMemories: (signal?: AbortSignal) => listMemories(signal),
  forgetMemory: (id: string) => forgetMemory(id),
  forgetAllMemories: () => forgetAllMemories(),
}));

function memory(overrides: Partial<StoredMemory> = {}): StoredMemory {
  return {
    memory_id: "m1",
    kind: "explicit_remember",
    content: "my desk is on floor three",
    score: 1,
    active: true,
    created_at: "2026-09-01T10:00:00+00:00",
    updated_at: "2026-09-01T10:00:00+00:00",
    expires_at: null,
    source_session_id: "session-a",
    ...overrides,
  };
}

// Seven, because a session's own list stops at five: a panel that quietly
// inherited that cap would still look correct with three rows.
const SEVEN = Array.from({ length: 7 }, (_, index) =>
  memory({ memory_id: `m${index}`, content: `memory number ${index}` })
);

beforeEach(() => {
  listMemories.mockReset().mockResolvedValue(SEVEN);
  forgetMemory.mockReset().mockResolvedValue({ ok: true, memory_id: "m0" });
  forgetAllMemories.mockReset().mockResolvedValue({ ok: true, forgotten: 7 });
});

afterEach(cleanup);

describe("the long-term memory panel", () => {
  it("shows every stored memory, not the five one session would use", async () => {
    render(<MemoryPanel />);

    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(7));
    expect(screen.getByText("memory number 6")).toBeInTheDocument();
  });

  it("says how many are held", async () => {
    render(<MemoryPanel />);
    await waitFor(() => expect(screen.getByText("7")).toBeInTheDocument());
  });

  it("shows an expired memory and marks it expired", async () => {
    // It no longer reaches the model but it has not gone anywhere. Omitting it
    // would report less stored than is stored, and leave no way to remove it.
    listMemories.mockResolvedValue([
      memory({ memory_id: "old", content: "a stale reminder", active: false, expires_at: "2026-01-01T00:00:00+00:00" }),
    ]);
    render(<MemoryPanel />);

    await waitFor(() => expect(screen.getByText("a stale reminder")).toBeInTheDocument());
    expect(screen.getByText("features.memory.expired")).toBeInTheDocument();
  });

  it("de-emphasises an expired row without dimming its text", () => {
    // `opacity` composites the subtree and is absent from
    // `getComputedStyle().color`, so a contrast audit walks past it. Measured:
    // `--text-muted` under `opacity-70` goes from 5.56 to 2.97 and fails AA.
    // The class list is the only place this is checkable without a browser.
    listMemories.mockResolvedValue([memory({ active: false, expires_at: "2026-01-01T00:00:00+00:00" })]);
    render(<MemoryPanel />);

    return waitFor(() => {
      const row = screen.getByRole("listitem");
      expect(row.className.split(" ")).not.toContainEqual(expect.stringMatching(/^opacity-/));
      expect(row.className).toContain("bg-surface-muted");
    });
  });

  it("deletes one memory and drops it from the list", async () => {
    listMemories.mockResolvedValue([memory({ memory_id: "m0", content: "first" }), memory({ memory_id: "m1", content: "second" })]);
    render(<MemoryPanel />);
    await waitFor(() => expect(screen.getByText("first")).toBeInTheDocument());

    await userEvent.click(screen.getAllByRole("button", { name: /forgetOne/ })[0]);

    expect(forgetMemory).toHaveBeenCalledWith("m0");
    await waitFor(() => expect(screen.queryByText("first")).toBeNull());
    expect(screen.getByText("second")).toBeInTheDocument();
  });

  it("keeps the row when deleting it fails", async () => {
    // A row that vanishes on a failed request tells the reader the memory is
    // gone while the system still holds it -- the worst answer available here.
    listMemories.mockResolvedValue([memory({ memory_id: "m0", content: "first" })]);
    forgetMemory.mockRejectedValue(new Error("nope"));
    render(<MemoryPanel />);
    await waitFor(() => expect(screen.getByText("first")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /forgetOne/ }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("nope"));
    expect(screen.getByText("first")).toBeInTheDocument();
  });

  it("asks before deleting everything, and deletes nothing if told no", async () => {
    render(<MemoryPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(7));

    await userEvent.click(screen.getByRole("button", { name: "features.memory.forgetAll" }));
    expect(forgetAllMemories).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "common.cancel" }));

    expect(forgetAllMemories).not.toHaveBeenCalled();
    expect(screen.getAllByRole("listitem")).toHaveLength(7);
  });

  it("deletes everything once confirmed", async () => {
    render(<MemoryPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(7));

    await userEvent.click(screen.getByRole("button", { name: "features.memory.forgetAll" }));
    await userEvent.click(screen.getByRole("button", { name: "features.memory.forgetAllConfirm" }));

    expect(forgetAllMemories).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryAllByRole("listitem")).toHaveLength(0));
    expect(screen.getByRole("status")).toHaveTextContent("features.memory.forgotAll:7");
  });

  it("does not report an empty record when the request failed", async () => {
    // The same mistake as a metrics bar reading 0% because nothing has been
    // measured: absence of an answer is not an answer of zero.
    listMemories.mockRejectedValue(new Error("gateway is down"));
    render(<MemoryPanel />);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("gateway is down"));
    expect(screen.queryByText("features.memory.empty")).toBeNull();
  });

  it("says so plainly when nothing is stored", async () => {
    listMemories.mockResolvedValue([]);
    render(<MemoryPanel />);

    await waitFor(() => expect(screen.getByText("features.memory.empty")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "features.memory.forgetAll" })).toBeNull();
  });
});
