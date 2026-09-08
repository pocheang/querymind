// @vitest-environment jsdom
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BROWSER_OWNED, SHORTCUTS, type ShortcutSpec } from "@/components/keyboardShortcuts";
import { useAppShortcuts } from "@/hooks/useAppShortcuts";
import { ChatComposer } from "@/pages/chat/components/ChatComposer";
import { useChatStore } from "@/stores/useChatStore";

/**
 * The guard for the whole defect class, not for the five instances of it.
 *
 * `KeyboardHelp` promised `Ctrl+K`, `Ctrl+N`, `Ctrl+B`, `Ctrl+W` and `Ctrl+R`
 * from the day it was written and the app implemented none of them. Nothing
 * could report that, because the documentation was a literal inside the
 * component and the handlers were somewhere else entirely -- there was no
 * place where the two met.
 *
 * They meet here. Each row of the shipped list is FIRED at a live handler and
 * has to be claimed. A row added with nothing behind it fails; a handler
 * deleted while its row stays fails. Parametrized per shortcut so a failure
 * names the key rather than the list.
 *
 * `Shift+Enter` is the one row asserted differently and deliberately: it is the
 * textarea's own behaviour, so what must be true is that NOTHING claims it --
 * the composer sending on it would be the defect.
 */

afterEach(() => {
  cleanup();
  useChatStore.getState().reset();
});

// --- the two harnesses a shortcut can live in ---

function AppHarness(props: Parameters<typeof useAppShortcuts>[0]) {
  useAppShortcuts(props);
  return null;
}

function mountApp() {
  const spies = { onCommandPalette: vi.fn(), onShortcutHelp: vi.fn(), onNewSession: vi.fn() };
  render(<AppHarness {...spies} />);
  return spies;
}

function mountComposer(isSending: boolean) {
  const noop = vi.fn();
  const spies = { onAsk: vi.fn().mockResolvedValue(undefined), onStop: vi.fn() };
  render(
    <ChatComposer
      questionRef={createRef<HTMLTextAreaElement>() as React.MutableRefObject<HTMLTextAreaElement | null>}
      chatUploadInputRef={createRef<HTMLInputElement>() as React.MutableRefObject<HTMLInputElement | null>}
      isSending={isSending}
      quickPrompts={[]}
      onComposerDragEnter={noop}
      onComposerDragOver={noop}
      onComposerDragLeave={noop}
      onComposerDrop={vi.fn().mockResolvedValue(undefined)}
      onChatUploadChange={vi.fn().mockResolvedValue(undefined)}
      {...spies}
    />
  );
  return spies;
}

const init = (spec: ShortcutSpec) => ({
  key: spec.event.key,
  ctrlKey: spec.event.mod === true,
  shiftKey: spec.event.shift === true,
  bubbles: true,
  cancelable: true,
});

/** Did anything at all respond -- a spy, the store, or a preventDefault? */
function fire(spec: ShortcutSpec): boolean {
  if (spec.scope === "app") {
    const spies = mountApp();
    const before = JSON.stringify([
      useChatStore.getState().sidebarOpen,
      useChatStore.getState().sidebarCollapsed,
    ]);
    const event = new KeyboardEvent("keydown", init(spec));
    window.dispatchEvent(event);
    const after = JSON.stringify([
      useChatStore.getState().sidebarOpen,
      useChatStore.getState().sidebarCollapsed,
    ]);
    return (
      event.defaultPrevented ||
      before !== after ||
      Object.values(spies).some((s) => s.mock.calls.length > 0)
    );
  }

  useChatStore.getState().setQuestion("a draft");
  const spies = mountComposer(spec.whileSending === true);
  const textarea = screen.getByRole("textbox");
  const handled = fireEvent.keyDown(textarea, init(spec)) === false;
  const cleared = useChatStore.getState().question === "";
  return handled || cleared || Object.values(spies).some((s) => s.mock.calls.length > 0);
}

describe("every documented shortcut is implemented", () => {
  const documented = SHORTCUTS.filter((s) => s.event.shift !== true);

  it.each(documented.map((s) => [s.keys.join("+") + (s.whileSending ? " (while sending)" : ""), s] as const))(
    "%s is claimed by a handler",
    (_name, spec) => {
      expect(fire(spec)).toBe(true);
    }
  );

  it("does not claim Shift+Enter, which is the textarea's own newline", () => {
    const spec = SHORTCUTS.find((s) => s.event.shift === true);
    expect(spec).toBeTruthy();
    const spies = mountComposer(false);
    fireEvent.keyDown(screen.getByRole("textbox"), init(spec as ShortcutSpec));
    expect(spies.onAsk).not.toHaveBeenCalled();
  });
});

describe("keys the browser owns", () => {
  it.each(BROWSER_OWNED.map((k) => [`Ctrl+${k.key.toUpperCase()}`, k] as const))(
    "%s is left alone",
    (_name, k) => {
      // Not documented...
      expect(SHORTCUTS.some((s) => s.event.key === k.key && s.event.mod === k.mod)).toBe(false);
      // ...and not silently claimed either.
      mountApp();
      const event = new KeyboardEvent("keydown", { key: k.key, ctrlKey: true, bubbles: true, cancelable: true });
      window.dispatchEvent(event);
      expect(event.defaultPrevented).toBe(false);
    }
  );
});
