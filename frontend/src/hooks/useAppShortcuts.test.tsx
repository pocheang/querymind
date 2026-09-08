// @vitest-environment jsdom
import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/react";

import { useAppShortcuts } from "@/hooks/useAppShortcuts";
import { useChatStore } from "@/stores/useChatStore";

/**
 * These shortcuts were DOCUMENTED and not implemented.
 *
 * `KeyboardHelp` listed Ctrl+K, Ctrl+N, Ctrl+B, Ctrl+W and Ctrl+R from the day
 * it was written, and the only keydown handler in the whole app was the one
 * that opened that same sheet. Nothing failed -- a shortcut that does nothing
 * looks exactly like a shortcut you pressed wrong -- which is why this is
 * pinned by test rather than left to a manual pass.
 *
 * The suite asserts the pairing in both directions: the keys that must work,
 * and the two the browser owns, which must NOT be claimed. Claiming Ctrl+W
 * would mean fighting the browser for "close tab" and losing in a way the user
 * experiences as the page eating their keystroke.
 */

// The store is real; only the callbacks are spies.
function Harness(props: Parameters<typeof useAppShortcuts>[0]) {
  useAppShortcuts(props);
  return null;
}

const press = (key: string, init: KeyboardEventInit = {}) => {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...init });
  window.dispatchEvent(event);
  return event;
};

afterEach(() => {
  cleanup();
  useChatStore.getState().reset();
});

describe("the app-wide keyboard shortcuts", () => {
  it("opens the command palette on Ctrl+K and on Cmd+K", () => {
    const onCommandPalette = vi.fn();
    render(<Harness onCommandPalette={onCommandPalette} onShortcutHelp={vi.fn()} />);

    expect(press("k", { ctrlKey: true }).defaultPrevented).toBe(true);
    expect(press("K", { metaKey: true }).defaultPrevented).toBe(true);
    expect(onCommandPalette).toHaveBeenCalledTimes(2);
  });

  it("opens the shortcut sheet on ? and on Ctrl+/", () => {
    const onShortcutHelp = vi.fn();
    render(<Harness onCommandPalette={vi.fn()} onShortcutHelp={onShortcutHelp} />);

    press("?");
    press("/", { ctrlKey: true });
    expect(onShortcutHelp).toHaveBeenCalledTimes(2);
  });

  it("does not fire ? while the user is typing", () => {
    const onShortcutHelp = vi.fn();
    render(<Harness onCommandPalette={vi.fn()} onShortcutHelp={onShortcutHelp} />);

    const input = document.createElement("textarea");
    document.body.appendChild(input);
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "?", bubbles: true, cancelable: true }));
    expect(onShortcutHelp).not.toHaveBeenCalled();
    input.remove();
  });

  it("toggles the sidebar on Ctrl+B, by the mechanism the width calls for", () => {
    render(<Harness onCommandPalette={vi.fn()} onShortcutHelp={vi.fn()} />);

    // Wide: the sidebar is an in-flow column, so `sidebarCollapsed` moves.
    window.innerWidth = 1440;
    const collapsedBefore = useChatStore.getState().sidebarCollapsed;
    press("b", { ctrlKey: true });
    expect(useChatStore.getState().sidebarCollapsed).toBe(!collapsedBefore);
    expect(useChatStore.getState().sidebarOpen).toBe(false);

    // Narrow: it is an off-canvas drawer, so `sidebarOpen` moves instead.
    window.innerWidth = 800;
    press("b", { ctrlKey: true });
    expect(useChatStore.getState().sidebarOpen).toBe(true);
  });

  it("creates a session on Ctrl+N only where one can be created", () => {
    const onNewSession = vi.fn();
    const { unmount } = render(
      <Harness onCommandPalette={vi.fn()} onShortcutHelp={vi.fn()} onNewSession={onNewSession} />
    );
    expect(press("n", { ctrlKey: true }).defaultPrevented).toBe(true);
    expect(onNewSession).toHaveBeenCalledTimes(1);
    unmount();

    // Without the callback -- every route that is not the chat view -- the key
    // is left to the browser rather than swallowed.
    render(<Harness onCommandPalette={vi.fn()} onShortcutHelp={vi.fn()} />);
    expect(press("n", { ctrlKey: true }).defaultPrevented).toBe(false);
  });

  it("leaves Ctrl+W and Ctrl+R to the browser", () => {
    render(<Harness onCommandPalette={vi.fn()} onShortcutHelp={vi.fn()} onNewSession={vi.fn()} />);

    // The help sheet used to promise both. The browser owns them -- close tab
    // and reload -- so the fix was to stop promising, not to fight for them.
    expect(press("w", { ctrlKey: true }).defaultPrevented).toBe(false);
    expect(press("r", { ctrlKey: true }).defaultPrevented).toBe(false);
  });

  it("stops listening once unmounted", () => {
    const onCommandPalette = vi.fn();
    const { unmount } = render(<Harness onCommandPalette={onCommandPalette} onShortcutHelp={vi.fn()} />);
    unmount();
    press("k", { ctrlKey: true });
    expect(onCommandPalette).not.toHaveBeenCalled();
  });
});
