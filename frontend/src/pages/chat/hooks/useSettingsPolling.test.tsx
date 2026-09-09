// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSettingsPolling } from "@/pages/chat/hooks/useSettingsPolling";

/**
 * The hook tells a reader when an administrator changes the model answering
 * their questions. What is pinned here is that it asks ONCE per interval and
 * not once per render.
 *
 * It used to key its effect on `[onNotify, t]`. react-i18next returns a fresh
 * `t` on most renders and the notifier is a new closure each time, so the effect
 * tore down and re-ran constantly -- and each run repeated its seeding fetch.
 * Measured in a real browser on an IDLE page: three requests in thirty seconds
 * against the one a 25s interval intends. While an answer streams, the chat page
 * re-renders continuously, so the real figure is much worse.
 *
 * The mock below returns a fresh `t` per render on purpose: that is what makes
 * the regression reproducible rather than hypothetical.
 */

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join(",")}` : key,
    i18n: { language: "en" },
  }),
}));

const getActiveModel = vi.fn();
vi.mock("@/lib/api", () => ({
  appApi: {
    getActiveModel: () => getActiveModel(),
  },
}));

function Harness({ onNotify }: { onNotify: (m: string, t: "success" | "error" | "info", d?: number) => void }) {
  // A NEW closure every render, which is what the chat page passes.
  useSettingsPolling({ onNotify: (...args) => onNotify(...args) });
  return null;
}

beforeEach(() => {
  getActiveModel.mockReset();
  getActiveModel.mockResolvedValue({
    ok: true,
    managed_by_admin: true,
    provider: "anthropic",
    model: "claude-sonnet-5",
  });
});

afterEach(() => cleanup());

describe("the model-change poller", () => {
  it("seeds once, however often the component re-renders", async () => {
    const notify = vi.fn();
    const { rerender } = render(<Harness onNotify={notify} />);
    await waitFor(() => expect(getActiveModel).toHaveBeenCalledTimes(1));

    for (let i = 0; i < 10; i += 1) rerender(<Harness onNotify={notify} />);

    // No interval has elapsed, so the count must not have moved. Keyed on
    // `[onNotify, t]` this reached 11.
    await waitFor(() => expect(getActiveModel).toHaveBeenCalledTimes(1));
  });

  it("says nothing on the first read", async () => {
    const notify = vi.fn();
    render(<Harness onNotify={notify} />);
    await waitFor(() => expect(getActiveModel).toHaveBeenCalledTimes(1));

    // The first read only establishes the baseline. Announcing it would tell
    // every reader on every page load that an administrator had just changed
    // the model, which is the failure the empty-metrics guard exists for too.
    expect(notify).not.toHaveBeenCalled();
  });

  it("survives a failed read without notifying", async () => {
    const notify = vi.fn();
    getActiveModel.mockRejectedValue(new Error("network"));
    render(<Harness onNotify={notify} />);

    await waitFor(() => expect(getActiveModel).toHaveBeenCalledTimes(1));
    expect(notify).not.toHaveBeenCalled();
  });
});
