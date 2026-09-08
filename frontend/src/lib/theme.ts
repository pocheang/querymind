const THEME_KEY = "theme_preference";

/**
 * Pin the document to the amber theme.
 *
 * The token layer is written as `:root, [data-theme="amber"]`, so a second
 * theme is a matter of adding one block and changing what this function
 * writes -- the indirection is kept for that reason even though there is only
 * one theme today.
 *
 * The stored preference is removed rather than read: there is nothing to
 * choose between yet, and a stale value from an earlier build would name a
 * theme that no longer has a token block.
 */
export function applyAmberTheme() {
  document.documentElement.dataset.theme = "amber";

  try {
    localStorage.removeItem(THEME_KEY);
  } catch {
    // Storage can be unavailable in privacy-restricted or sandboxed contexts.
  }
}
