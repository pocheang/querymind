// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { KeyboardHelp } from "@/components/KeyboardHelp";

/**
 * The sheet documents shortcuts, so what it must never do is document one the
 * app does not implement. It listed five such keys for as long as it existed.
 */
afterEach(cleanup);

describe("the keyboard shortcut sheet", () => {
  it("renders nothing while closed", () => {
    const { container } = render(<KeyboardHelp open={false} onClose={vi.fn()} />);
    expect(container.innerHTML).toBe("");
  });

  it("closes on Escape", () => {
    // It had its own listener for this until the listener moved out to
    // `useAppShortcuts`; the move dropped Escape and nothing noticed.
    const onClose = vi.fn();
    render(<KeyboardHelp open onClose={onClose} />);
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("documents no shortcut the browser owns", () => {
    render(<KeyboardHelp open onClose={vi.fn()} />);
    const keys = [...document.querySelectorAll("kbd")].map((k) => k.textContent);
    // Ctrl+W closes the tab and Ctrl+R reloads; a page cannot take them back,
    // so promising them taught the reader something false.
    const rows = [...document.querySelectorAll("dl > div")].map((r) =>
      [...r.querySelectorAll("kbd")].map((k) => k.textContent).join("+")
    );
    expect(keys.length).toBeGreaterThan(0);
    expect(rows).not.toContain("Ctrl+W");
    expect(rows).not.toContain("Ctrl+R");
    expect(rows).toContain("Ctrl+K");
    expect(rows).toContain("Ctrl+B");
    expect(rows).toContain("Ctrl+N");
  });

  it("names Ctrl+K as the palette rather than a search box", () => {
    render(<KeyboardHelp open onClose={vi.fn()} />);
    expect(screen.queryByText(/focus.*search/i)).toBeNull();
  });
});
