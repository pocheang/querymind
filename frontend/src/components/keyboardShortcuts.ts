/**
 * Every keyboard shortcut this app claims to have.
 *
 * It is DATA, in its own module, for one reason: `keyboardShortcuts.test.ts`
 * walks this list and fires each entry at a live handler, so a row added here
 * with nothing behind it fails the suite. The list used to be a literal inside
 * `KeyboardHelp`, where it drifted into promising five shortcuts that did not
 * exist -- `Ctrl+K`, `Ctrl+N`, `Ctrl+B`, `Ctrl+W`, `Ctrl+R` -- for as long as
 * the component had existed, with nothing able to notice.
 *
 * `scope` says which handler owns it, because they are reached differently:
 * `app` is `useAppShortcuts` on `window`, `composer` is the textarea's own
 * `onKeyDown`. A test cannot check "is this implemented" without knowing where
 * to knock.
 */
export interface ShortcutSpec {
  /** As rendered, one `<kbd>` per entry. */
  keys: string[];
  /** The event this is fired as. `mod` means Ctrl on Windows, Cmd on macOS. */
  event: { key: string; mod?: boolean; shift?: boolean };
  scope: "app" | "composer";
  descriptionKey: string;
  categoryKey: string;
  /** Only fires while an answer is streaming. */
  whileSending?: boolean;
}

const MESSAGE = "components.keyboard.categories.message";
const NAVIGATION = "components.keyboard.categories.navigation";
const OTHER = "components.keyboard.categories.other";

export const SHORTCUTS: ShortcutSpec[] = [
  {
    keys: ["Ctrl", "Enter"],
    event: { key: "Enter", mod: true },
    scope: "composer",
    descriptionKey: "components.keyboard.shortcuts.send",
    categoryKey: MESSAGE,
  },
  {
    keys: ["Shift", "Enter"],
    event: { key: "Enter", shift: true },
    scope: "composer",
    descriptionKey: "components.keyboard.shortcuts.newline",
    categoryKey: MESSAGE,
  },
  {
    keys: ["Esc"],
    event: { key: "Escape" },
    scope: "composer",
    descriptionKey: "components.keyboard.shortcuts.clear",
    categoryKey: MESSAGE,
  },
  {
    keys: ["Esc"],
    event: { key: "Escape" },
    scope: "composer",
    whileSending: true,
    descriptionKey: "components.keyboard.shortcuts.stop",
    categoryKey: MESSAGE,
  },
  {
    keys: ["Ctrl", "K"],
    event: { key: "k", mod: true },
    scope: "app",
    descriptionKey: "components.keyboard.shortcuts.commandPalette",
    categoryKey: NAVIGATION,
  },
  {
    keys: ["Ctrl", "N"],
    event: { key: "n", mod: true },
    scope: "app",
    descriptionKey: "components.keyboard.shortcuts.newSession",
    categoryKey: NAVIGATION,
  },
  {
    keys: ["Ctrl", "B"],
    event: { key: "b", mod: true },
    scope: "app",
    descriptionKey: "components.keyboard.shortcuts.toggleSidebar",
    categoryKey: NAVIGATION,
  },
  {
    keys: ["?"],
    event: { key: "?" },
    scope: "app",
    descriptionKey: "components.keyboard.shortcuts.showHelp",
    categoryKey: OTHER,
  },
  {
    keys: ["Ctrl", "/"],
    event: { key: "/", mod: true },
    scope: "app",
    descriptionKey: "components.keyboard.shortcuts.showHelp",
    categoryKey: OTHER,
  },
];

/**
 * Keys the browser owns, which this app must never claim.
 *
 * `Ctrl+W` closes the tab and `Ctrl+R` reloads; a page cannot reliably take
 * either back, so a shortcut on one is a promise the user experiences as the
 * page eating a keystroke. Both were on the documented list until 2026-09-07.
 */
export const BROWSER_OWNED = [
  { key: "w", mod: true },
  { key: "r", mod: true },
  { key: "t", mod: true },
];
