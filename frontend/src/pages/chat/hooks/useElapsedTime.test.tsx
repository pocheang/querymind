// @vitest-environment jsdom
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { useElapsedTime } from "./useElapsedTime";

function Harness({ active, onTick }: { active: boolean; onTick: (ms: number) => void }) {
  onTick(useElapsedTime(active, 10));
  return null;
}

afterEach(() => cleanup());

describe("useElapsedTime", () => {
  it("stays at 0 while inactive", async () => {
    const seen: number[] = [];
    render(<Harness active={false} onTick={(ms) => seen.push(ms)} />);

    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(seen.every((ms) => ms === 0)).toBe(true);
  });

  it("ticks upward while active", async () => {
    const seen: number[] = [];
    render(<Harness active={true} onTick={(ms) => seen.push(ms)} />);

    await waitFor(() => expect(seen[seen.length - 1]).toBeGreaterThan(0));
  });

  it("resets to 0 when it goes active again after being inactive", async () => {
    const seen: number[] = [];
    const { rerender } = render(<Harness active={true} onTick={(ms) => seen.push(ms)} />);
    await waitFor(() => expect(seen[seen.length - 1]).toBeGreaterThan(0));

    rerender(<Harness active={false} onTick={(ms) => seen.push(ms)} />);
    expect(seen[seen.length - 1]).toBe(0);

    seen.length = 0;
    rerender(<Harness active={true} onTick={(ms) => seen.push(ms)} />);

    expect(seen[0]).toBe(0);
    await waitFor(() => expect(seen[seen.length - 1]).toBeGreaterThan(0));
  });
});
