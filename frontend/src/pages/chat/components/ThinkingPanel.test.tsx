// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ThinkingPanel } from "@/pages/chat/components/ThinkingPanel";

/**
 * Three states, mirroring MessageCard's existing "Thought for Ns" toggle
 * for `execution_steps`: reasoning-in-progress (auto-expanded, live text),
 * settled (collapsed by default, real duration), and a manual toggle that
 * sticks regardless of how `isStreaming` changes afterward.
 */

afterEach(() => cleanup());

describe("ThinkingPanel", () => {
  it("renders nothing when there is no reasoning text", () => {
    const { container } = render(<ThinkingPanel reasoning="" isStreaming={false} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("auto-expands and shows the live text while streaming", () => {
    render(<ThinkingPanel reasoning="Step 1: analyze the question." isStreaming={true} />);

    const toggle = screen.getByRole("button");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Step 1: analyze the question.")).toBeInTheDocument();
  });

  it("collapses by default once settled, and shows the real duration", () => {
    render(<ThinkingPanel reasoning="Full reasoning text." durationMs={4200} isStreaming={false} />);

    const toggle = screen.getByRole("button");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Full reasoning text.")).not.toBeInTheDocument();
    // 4200ms -> 4s, via the same {{seconds}} interpolation MessageCard's
    // existing toggle already uses.
    expect(toggle.textContent).toContain("4");
  });

  /**
   * `durationMs` only ever arrives with the final response, while
   * `isStreaming` goes false the moment the ANSWER channel starts -- so for
   * the whole time the answer is streaming, this panel is settled with no
   * measured duration. `durationMs || 0` reported that as "Thought for 0s":
   * a confident number for something nothing had measured yet.
   */
  it("reports no duration rather than zero while one has not been measured", () => {
    render(<ThinkingPanel reasoning="Full reasoning text." isStreaming={false} />);

    const toggle = screen.getByRole("button");
    expect(toggle.textContent).toContain("Reasoning");
    expect(toggle.textContent).not.toContain("0");
  });

  it("does the same for a real duration that rounds down to zero seconds", () => {
    // 400ms is a measured value, and "Thought for 0s" is still the wrong
    // claim about it.
    render(<ThinkingPanel reasoning="Full reasoning text." durationMs={400} isStreaming={false} />);

    expect(screen.getByRole("button").textContent).not.toContain("0");
  });

  /**
   * An `aria-label` REPLACES a button's text as its accessible name. A generic
   * "expand or collapse reasoning" was therefore the only thing a screen
   * reader heard, and the state a sighted reader is shown -- still thinking,
   * or how long it took -- never reached one. `aria-expanded` already carries
   * the toggle affordance.
   */
  it("names itself by the state it shows, not by the action it performs", () => {
    render(<ThinkingPanel reasoning="Full reasoning text." durationMs={4200} isStreaming={false} />);

    expect(screen.getByRole("button", { name: /Thought for 4s/ })).toBeInTheDocument();
  });

  it("names itself by the no-duration label when there is no duration", () => {
    render(<ThinkingPanel reasoning="Full reasoning text." isStreaming={false} />);

    expect(screen.getByRole("button", { name: "Reasoning" })).toBeInTheDocument();
  });

  it("expands on click while settled, revealing the reasoning text", () => {
    render(<ThinkingPanel reasoning="Full reasoning text." isStreaming={false} />);

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Full reasoning text.")).toBeInTheDocument();
  });

  it("a manual collapse while streaming stays collapsed once streaming ends", () => {
    const { rerender } = render(<ThinkingPanel reasoning="Step 1: analyze" isStreaming={true} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "true");

    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");

    // Reasoning finishes and the answer starts -- isStreaming flips false.
    // The reader's own choice must not be overridden by that transition.
    rerender(<ThinkingPanel reasoning="Step 1: analyze the question fully." durationMs={2000} isStreaming={false} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });
});
