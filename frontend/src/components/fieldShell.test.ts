import { readFileSync, readdirSync } from "node:fs";
import { extname, join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * `field-shell` moves a focus ring; it must never remove one.
 *
 * `core/surfaces.css` gives every `input, textarea, select` a 3px
 * `:focus-visible` ring, which is what an unclassed field needs -- `reset.css`
 * is this app's preflight, so without it a bare field would show focus not at
 * all. But it also reached the bare input inside a bordered wrapper, and then
 * two elements drew an affordance for one control: measured on the login field,
 * three concentric amber marks, the wrapper's 2px ring outside its 1px accent
 * border and the input's own 3px ring inside it.
 *
 * `field-shell` cancels the inner one. That is only safe while the wrapper
 * shows focus itself, so this asserts the pairing at every call site. Getting
 * it wrong produces a field with NO focus indicator, which is worse than the
 * ugly one it replaced and is invisible to anyone using a mouse -- exactly the
 * failure that survives review.
 *
 * Source text rather than a rendered DOM on purpose: jsdom has no cascade and
 * no layers, so it cannot tell which ring won. What is checkable here is the
 * pairing, and the browser measurement is recorded in CLAUDE.md.
 */

const SRC = "src";

/** Something on this element makes focus visible while a child holds it. */
const SHOWS_FOCUS = [
  "focus-within:ring",
  "focus-within:border",
  // The composer capsule lights its whole gradient edge; see app-utilities.css.
  "composer-ring",
];

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sources(path);
    return [".ts", ".tsx"].includes(extname(entry.name)) && !entry.name.includes(".test.") ? [path] : [];
  });
}

/** The class lists that mention `field-shell`, one per occurrence. */
function fieldShellSites(): { file: string; classes: string }[] {
  const sites: { file: string; classes: string }[] = [];
  for (const file of sources(SRC)) {
    const text = readFileSync(file, "utf8");
    if (!text.includes("field-shell")) continue;
    for (const line of text.split("\n")) {
      if (!line.includes("field-shell")) continue;
      sites.push({ file, classes: line });
    }
  }
  return sites;
}

describe("field-shell", () => {
  const sites = fieldShellSites();

  it("is actually used, so the rest of this file is not vacuous", () => {
    expect(sites.length).toBeGreaterThanOrEqual(5);
  });

  it.each(sites.map((s) => [s.file, s.classes] as const))(
    "%s keeps a focus affordance of its own",
    (_file, classes) => {
      // A class list mentioning `field-shell` may be split across lines by the
      // formatter, so accept the affordance anywhere in the same declaration.
      expect(SHOWS_FOCUS.some((marker) => classes.includes(marker))).toBe(true);
    }
  );

  it("is declared once, and inside a named layer", () => {
    // It styles a DESCENDANT, which no class list on the wrapper can express,
    // so it lives in CSS rather than in a className, and a second copy of it
    // would be silent.
    //
    // The layer is the load-bearing half. `app-utilities.css` is imported
    // WITHOUT a layer, because `@utility` is what places its rules in
    // Tailwind's `utilities` layer -- so a plain rule here that does not name
    // one is UNLAYERED and outranks every cascade layer, including the
    // utilities a call site would use to override it. This was written as
    // `@utility field-shell { & ... }` until `css:S8776` pointed out that `&`
    // has no scoping root in a file a CSS parser reads as plain CSS; the
    // rewrite is only safe because the layer is named explicitly.
    const css = readFileSync(join(SRC, "styles/core/app-utilities.css"), "utf8");
    expect(css.match(/\.field-shell[^{]*\{/g) ?? []).toHaveLength(1);
    expect(css).toMatch(/@layer utilities\s*\{\s*\.field-shell[^}]*box-shadow:\s*none/);
  });
});

/**
 * One focus idiom for the whole app.
 *
 * `:focus` fires on a mouse click; `:focus-visible` is the browser's judgement
 * that somebody is navigating by keyboard. The primitives used the second and
 * twelve files still used the first, so clicking a field in the admin console
 * rang and clicking one in the settings drawer did not -- the same drift
 * already recorded for the class strings copied inline into IntegrationsPanel.
 *
 * The exception is real and is not a style preference: Radix moves focus
 * programmatically for a roving tabindex, and `:focus-visible` does not match
 * that, so a menu item styled with it would stop highlighting as you arrow
 * through the menu.
 */
describe("focus affordances", () => {
  const RING_UTILITIES = /focus:(ring|outline|border)-/;
  const ALLOWED = ["dropdown-menu.tsx"];

  const offenders = sources(SRC)
    .filter((file) => !ALLOWED.some((name) => file.endsWith(name)))
    .flatMap((file) =>
      readFileSync(file, "utf8")
        .split(/\r?\n/)
        .flatMap((line, index) =>
          // A comment ABOUT the idiom is not a use of it.
          RING_UTILITIES.test(line) && !line.trimStart().startsWith("*") && !line.trimStart().startsWith("//")
            ? [`${file}:${index + 1}`]
            : []
        )
    );

  it("uses focus-visible everywhere except the Radix menu", () => {
    expect(offenders).toEqual([]);
  });

  it("still finds the Radix menu using the plain form, so the rule is not vacuous", () => {
    const menu = readFileSync(join(SRC, "components/ui/dropdown-menu.tsx"), "utf8");
    expect(menu).toMatch(/focus:bg-/);
  });
});
