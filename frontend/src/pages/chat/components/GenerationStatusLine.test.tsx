// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { GenerationStatusLine } from "@/pages/chat/components/GenerationStatusLine";
import type { ExecutionEvent } from "@/features/execution-trace/types";

afterEach(() => cleanup());

const event = (stage: ExecutionEvent["stage"]): ExecutionEvent => ({
  version: "1",
  stage,
  status: "completed",
  duration_ms: 12,
  message: "",
  metadata: [],
  occurred_at: "2026-09-15T00:00:00Z",
});

describe("GenerationStatusLine", () => {
  it("renders nothing when no run is in flight", () => {
    const { container } = render(<GenerationStatusLine events={[]} active={false} />);

    expect(container).toBeEmptyDOMElement();
  });

  /**
   * `<output>` is an implicit `aria-live="polite"` region. The clock inside
   * it changes every 250ms, so leaving it in the accessibility tree turned
   * one announcement per phase into four a second -- a running timer read
   * aloud over and over. The phrase is the content; the clock is decoration.
   */
  it("keeps the ticking clock out of the live region it sits in", () => {
    render(<GenerationStatusLine events={[]} active={true} />);

    expect(screen.getByText("0:00")).toHaveAttribute("aria-hidden", "true");
  });

  it("announces the phase the trace implies, and that text is not hidden", () => {
    // `route` finished, so retrieval is what is happening now.
    render(<GenerationStatusLine events={[event("route")]} active={true} />);

    const phase = screen.getByText("features.executionTrace.phase.retrieving");
    expect(phase).not.toHaveAttribute("aria-hidden");
    expect(screen.getByRole("status")).toContainElement(phase);
  });
});
