import { useEffect } from "react";

import { useSidebarToggle } from "@/hooks/useSidebarToggle";

interface AppShortcuts {
  onCommandPalette: () => void;
  onShortcutHelp: () => void;
  onNewSession?: () => void;
}

/** Typing somewhere should not fire a single-key shortcut. */
function isTyping(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable;
}

/**
 * The app-wide keyboard shortcuts.
 *
 * These are the ones `KeyboardHelp` has documented since it was written, and
 * until now **none of them existed** -- the sheet listed `Ctrl+K`, `Ctrl+N`,
 * `Ctrl+B`, `Ctrl+W` and `Ctrl+R` and the only handler in the whole app was
 * the one that opens the sheet itself. A help panel that teaches shortcuts the
 * app does not implement is the same defect as a settings page reporting a
 * value the process does not use.
 *
 * `Ctrl+W` and `Ctrl+R` are deliberately NOT implemented and no longer
 * documented. The browser owns them -- close tab and reload -- and a page
 * cannot reliably take them back, so promising them is promising something the
 * user will experience as the browser winning. Both toggles live in the
 * command palette instead, which is reachable by a key the page may have.
 *
 * Mounted by `AppShell`, so they work on every signed-in route rather than on
 * the chat page alone.
 */
export function useAppShortcuts({ onCommandPalette, onShortcutHelp, onNewSession }: AppShortcuts) {
  const toggleSidebar = useSidebarToggle();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const mod = event.ctrlKey || event.metaKey;

      if (mod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onCommandPalette();
        return;
      }
      if (mod && event.key.toLowerCase() === "b") {
        event.preventDefault();
        toggleSidebar();
        return;
      }
      if (mod && event.key.toLowerCase() === "n" && onNewSession) {
        // Ctrl+N opens a browser window; preventDefault holds it in Chrome and
        // Edge for a page with focus, and where it does not, the palette entry
        // is the way in. Better to claim it and mostly work than to document
        // it and never work.
        event.preventDefault();
        onNewSession();
        return;
      }
      if (mod && event.key === "/") {
        event.preventDefault();
        onShortcutHelp();
        return;
      }
      if (event.key === "?" && !mod && !isTyping(event.target)) {
        event.preventDefault();
        onShortcutHelp();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCommandPalette, onShortcutHelp, onNewSession, toggleSidebar]);
}
