import { useEffect, useRef } from "react";

/**
 * Escape closes it, and focus goes back where it came from.
 *
 * Both overlays in this app are hand-rolled rather than Radix dialogs, so
 * neither gets this for free. `KeyboardHelp` used to implement Escape inside
 * its own key listener and lost it when that listener moved to
 * `useAppShortcuts`; `CommandPalette` never had it -- cmdk's bare `Command`
 * handles arrow keys and typing, not dismissal, and the string "Escape" does
 * not appear anywhere in its bundle. An overlay that only a mouse can close is
 * a trap for anyone who opened it from the keyboard, which for a ⌘K palette is
 * everyone.
 *
 * Focus restore matters for the same reason: the palette autofocuses its
 * input, so without this, closing leaves focus on `<body>` and the next Tab
 * starts from the top of the page.
 */
export function useDismissable(open: boolean, onDismiss: () => void) {
  const restoreTo = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    restoreTo.current = document.activeElement as HTMLElement | null;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      // Stop the app-wide handlers seeing it too: Escape means "close the
      // thing in front of me", not "close the thing behind it as well".
      event.stopPropagation();
      onDismiss();
    };

    // Capture phase, so this runs before anything inside the overlay claims it.
    window.addEventListener("keydown", onKeyDown, true);
    return () => {
      window.removeEventListener("keydown", onKeyDown, true);
      // Only take focus back if the overlay still holds it; a dismissal that
      // navigated somewhere has already put focus where it belongs.
      const active = document.activeElement;
      if (!active || active === document.body) restoreTo.current?.focus?.();
    };
  }, [open, onDismiss]);
}
