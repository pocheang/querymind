/* Which class names in `src/` do nothing at all?
 *
 * "Is it in a stylesheet?" cannot answer this, because most class names here
 * are Tailwind utilities no stylesheet declares. So ask the BUILD:
 * `dist/assets/*.css` plus the critical CSS inlined into `dist/index.html` is
 * every rule the browser receives. A class that reaches a `className` and
 * appears in none of it is inert -- it renders as nothing, and lint, tsc and
 * the tests are all blind to it.
 *
 * This is `surfaces.css` from the other side. That sweep found 28 of 39
 * selectors matching no element; this one finds an element carrying a name no
 * rule defines. `IntegrationsPanel` had two (`integrations-panel`,
 * `runtime-panel-empty`), left behind when the 2026-09-07 purge deleted the
 * sheets that defined them -- so its fields, list and headings rendered as raw
 * browser defaults inside a finished drawer, through a whole visual rewrite
 * and two contrast audits, with nothing reporting it.
 *
 * Run AFTER `npm run build`; without a build there is nothing to compare to.
 *
 * Two blind spots, both recorded rather than fixed, and both under-report:
 *
 *   - A variant-prefixed token (`hover:bg-x`) is skipped. Tailwind escapes the
 *     colon in the selector and matching that reliably costs more than the
 *     answer is worth.
 *   - A class assembled by interpolation is invisible, the same limit the
 *     surfaces.css sweep had. Missing one costs a finding; the opposite
 *     mistake would cost a wrongly deleted rule.
 *
 * Two earlier versions of this were wrong in ways worth keeping:
 *   1. It matched every hyphenated string literal, so it reported 134 hits --
 *      package names, model ids, `aria-*` attributes, DOM ids, ReactFlow edge
 *      ids, `cva` variant keys. A list that is 95% noise gets ignored.
 *   2. Narrowed to `className`, it then read `className="a b"` by searching the
 *      already-unquoted value for QUOTED strings, finding none -- so it scanned
 *      198 tokens instead of 386 and reported the two known-dead names clean.
 *      A scan that silently stops matching passes every later assertion.
 */
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, extname, basename } from "node:path";

const SRC = "src";
const DIST = "dist";

/* Names this check must not judge: each is read by something other than the
 * class-to-rule relationship -- `scripts/screenshots.mjs` finds the shell and
 * sidebar by class, several component tests assert on one, and the rest are
 * styled from `core/surfaces.css` by a rule reaching a descendant.
 *
 * `useSectionToggle` used to be the reason for some of them and is not any
 * more -- it stopped reaching into the document, which is exactly how
 * `topbar-menu-trigger` sat here exempting a class nothing emitted. Adding a
 * name is a claim that something reads it; say what, and the guard below
 * checks the claim is still true. */
const BEHAVIOURAL = new Set([
  "page-shell",
  "sidebar-collapsed",
  "composer-panel",
  "reactflow-wrapper",
  "confirm-dialog-overlay",
  "local-assistant-stream",
  "execution-trace-panel",
  "tool-approval-panel",
  "landing-root",
  "auth-root",
]);

const CLASSNAME = /className\s*=\s*(?:"([^"]*)"|\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\})/g;
const STRING = /"([^"\n]*)"|'([^'\n]*)'|`([^`$\n]*)`/g;
const PLAIN = /^[a-z][a-z0-9]*(?:-[a-z0-9.]+)+$/;

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(path));
    else if ([".ts", ".tsx"].includes(extname(entry.name)) && !entry.name.includes(".test.")) out.push(path);
  }
  return out;
}

/** The text of a `cn(` call, from its open paren to the matching one. */
function balanced(text, start) {
  let depth = 0;
  for (let i = start; i < text.length; i += 1) {
    if (text[i] === "(") depth += 1;
    else if (text[i] === ")") {
      depth -= 1;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return text.slice(start);
}

function deliveredCss() {
  const assets = join(DIST, "assets");
  if (!existsSync(assets)) {
    console.error("no build to compare against -- run `npm run build` first");
    process.exit(2);
  }
  const parts = readdirSync(assets)
    .filter((f) => f.endsWith(".css"))
    .map((f) => readFileSync(join(assets, f), "utf8"));
  // The critical CSS is INLINED into <head> and never emitted as an asset, so
  // reading assets alone reports `app-loading` -- which `core/critical.css`
  // really does define -- as dead. A blind spot in a dead-code finder is how a
  // live rule gets deleted.
  const index = join(DIST, "index.html");
  if (existsSync(index)) parts.push(readFileSync(index, "utf8"));
  // Backslashes are stripped so a selector can be matched as plain text.
  // Tailwind escapes the dot in a fractional utility -- `gap-1.5` is written
  // `.gap-1\.5` -- and the first port of this script compared against the raw
  // text and reported all 34 of them dead, which is the entire spacing scale.
  // Normalising here beats hand-escaping at every comparison; the only tokens
  // it could confuse are variant-prefixed ones, which are skipped anyway.
  return parts.join("\n").replaceAll("\\", "");
}

/** `className="a b c"` yields the class list itself; `className={...}` and
 *  `cn(...)` yield an expression whose STRING LITERALS are the classes.
 *  Treating both the same way is defect 2 in the header. */
function classValuesAndExpressions(path, text) {
  const values = [];
  const expressions = [];
  for (const match of text.matchAll(CLASSNAME)) {
    if (match[1] !== undefined) values.push(match[1]);
    else expressions.push(match[2] ?? "");
  }
  for (const match of text.matchAll(/\bcn\(/g)) expressions.push(balanced(text, match.index + match[0].length - 1));
  if (basename(path).endsWith("Classes.ts")) expressions.push(text);
  return { values, expressions };
}

/** String literals inside each expression region are class-name candidates too. */
function expandExpressions(values, expressions) {
  for (const region of expressions) {
    for (const match of region.matchAll(STRING)) values.push(match[1] ?? match[2] ?? match[3] ?? "");
  }
}

/** Record each plain, non-behavioural class token's occurrence in `found`. */
function recordTokens(found, values, path) {
  for (const value of values) {
    for (const token of value.split(/\s+/)) {
      if (PLAIN.test(token) && !BEHAVIOURAL.has(token)) {
        if (!found.has(token)) found.set(token, new Set());
        found.get(token).add(path);
      }
    }
  }
}

function classTokens() {
  const found = new Map();
  for (const path of walk(SRC)) {
    const text = readFileSync(path, "utf8");
    const { values, expressions } = classValuesAndExpressions(path, text);
    expandExpressions(values, expressions);
    recordTokens(found, values, path);
  }
  return found;
}

const css = deliveredCss();
const tokens = classTokens();

/* The escape list can only shrink. An entry naming a class `src/` no longer
   emits is exempting nothing, and it is how `topbar-menu-trigger` stayed in
   three places -- a rule, a comment claiming two readers, and this list --
   after the element was deleted. Same rule as SECRET_BASELINE in
   scripts/check_sensitive.py and KNOWN_OFFENDERS in tests/security/. */
const emitted = new Set(
  walk(SRC).flatMap((path) => readFileSync(path, "utf8").split(/[^\w-]+/))
);
const staleExemptions = [...BEHAVIOURAL].filter((name) => !emitted.has(name));
if (staleExemptions.length) {
  console.error("These BEHAVIOURAL entries exempt a class nothing in src/ emits:\n");
  for (const name of staleExemptions) console.error(`  ${name}`);
  console.error("\nDrop them: an exemption for something that does not exist hides nothing");
  console.error("and tells the next reader the class is still in use.");
  process.exit(1);
}
// `String.raw` so the pattern reads as the regex it becomes. Every escape here
// is load-bearing -- Tailwind escapes the dot in a fractional utility, so
// `gap-1.5` is delivered as `.gap-1\.5`, and an earlier version of this line
// that compared against raw text called the whole spacing scale dead.
// The escaped dot is its own constant (rather than a `String.raw` nested
// inside the outer one) because javascript:S4624 flags a nested template
// literal on sight, with no way to know both are already raw.
const ESCAPED_DOT = String.raw`\.`;
const dead = [...tokens].filter(
  ([token]) => !new RegExp(String.raw`\.${token.replaceAll(".", ESCAPED_DOT)}(?![\w-])`).test(css)
);

console.log(`class names reaching a className : ${tokens.size}`);
console.log(`present in the delivered CSS     : ${tokens.size - dead.length}`);
console.log(`PRESENT NOWHERE (inert)          : ${dead.length}`);

if (dead.length === 0) {
  console.log("\ndead classes ok - every class name in src/ resolves to a rule");
  process.exit(0);
}
console.error("\nThese class names render as nothing. Style the element, drop the name, or");
console.error("add it to BEHAVIOURAL with a note saying what reads it:\n");
// Sorted by the token explicitly. `dead` holds [string, Set] pairs, and a
// bare `.sort()` orders by each element's STRING form -- "token,[object Set]"
// -- which happens to read as alphabetical today and stops the moment the
// shape changes. That is what `javascript:S2871` is for.
for (const [token, files] of [...dead].sort((left, right) => left[0].localeCompare(right[0]))) {
  console.error(`  ${token.padEnd(26)} ${[...files].map((f) => basename(f)).join(", ")}`);
}
process.exit(1);
