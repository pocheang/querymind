import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

/**
 * A height-bounded frame must CLIP, not HIDE.
 *
 * `overflow: hidden` makes an element a scroll container that merely hides its
 * scrollbar. The browser can still scroll it -- on focus, on `scrollIntoView`,
 * on scroll anchoring while content streams in -- and with no scrollbar the
 * reader has no way to scroll it back. It stays wherever it was put, for the
 * life of the page.
 *
 * Measured on the chat column (2026-09-16, a real signed-in session): after a
 * few streamed answers it sat at `scrollTop: 344` with `scrollHeight` 2473
 * against a `clientHeight` of 862. Its three children summed to exactly 862 --
 * nothing overflowed -- yet the first one rendered at `top: -288`, so the top
 * of the conversation was off-screen and a 344px hole sat under the composer.
 * Nothing in the UI could recover it.
 *
 * The overflow that makes the frame scrollable comes from the message list
 * inside it (hiding that child dropped the frame's `scrollHeight` from 2473 to
 * 862), so it cannot be removed by tidying the frame's own children.
 * `overflow: clip` creates no scroll container at all, which makes the whole
 * class of trigger impossible without having to find which one fired:
 *
 *     overflow: hidden   scrollTop = 500  ->  500
 *     overflow: clip     scrollTop = 999  ->  0
 *
 * Same element, same moment, layout byte-identical.
 *
 * This is deliberately a source scan: jsdom computes no layout, so the property
 * cannot be measured in a component test. What it can do is stop the class
 * string from coming back.
 */

const SRC = join(process.cwd(), "src");

/** `min-h-0` and `h-screen` are how this codebase says "I am a bounded frame".
 *  A small box that clips for rounded corners carries neither, which is why
 *  `MarkdownBlock`'s code block and `ThinkingPanel`'s shell are not findings. */
const FRAME_MARKERS = ["min-h-0", "h-screen"];

/** How far from an `overflow-hidden` token a frame marker still counts as
 *  belonging to the same element. Wide enough to span a `cn()` call that puts
 *  the layout classes in one argument and the overflow in a ternary in the
 *  next -- which is exactly the shape `AppShell` uses, and a per-string-literal
 *  scan would have missed it. */
const WINDOW = 140;

function sources(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) sources(full, acc);
    else if (/\.tsx$/.test(entry) && !entry.includes(".test.")) acc.push(full);
  }
  return acc;
}

/** Every place a bounded frame is clipped with `overflow-hidden`. */
function hiddenFrames(text: string): string[] {
  const found: string[] = [];
  const token = /\boverflow-hidden\b/g;
  let match: RegExpExecArray | null;
  while ((match = token.exec(text)) !== null) {
    const from = Math.max(0, match.index - WINDOW);
    const near = text.slice(from, match.index + WINDOW);
    // A line that only talks ABOUT the rule is not a use of it.
    const line = text.slice(text.lastIndexOf("\n", match.index) + 1, text.indexOf("\n", match.index));
    if (line.trimStart().startsWith("*") || line.trimStart().startsWith("//")) continue;
    if (FRAME_MARKERS.some((marker) => near.includes(marker))) found.push(near.replace(/\s+/g, " ").trim());
  }
  return found;
}

const FRAMES = [
  "src/components/layout/AppShell.tsx",
  "src/pages/chat/components/ChatSidebar.tsx",
  "src/pages/chat/components/ChatWorkspace.tsx",
  "src/pages/ChatPage.tsx",
];

describe("bounded frames clip rather than hide", () => {
  it.each(FRAMES)("%s clips its frame", (relative) => {
    const text = readFileSync(join(process.cwd(), relative), "utf8");

    expect(text).toContain("overflow-clip");
    expect(hiddenFrames(text)).toEqual([]);
  });

  it("finds no bounded frame anywhere in src/ still using overflow-hidden", () => {
    const offenders = sources(SRC)
      .map((file) => ({ file: file.slice(SRC.length + 1), sites: hiddenFrames(readFileSync(file, "utf8")) }))
      .filter((entry) => entry.sites.length > 0);

    expect(offenders).toEqual([]);
  });

  /**
   * The scan reports "clean" and "matched nothing" identically, and a regex
   * that silently stops matching is a defect this repository has shipped
   * before. So: feed it the shipped class strings and require a finding.
   */
  it("can fail -- the shipped strings are all detected", () => {
    const shipped = [
      `<main className="relative flex min-h-0 flex-1 flex-col overflow-hidden">`,
      `<div className="flex h-screen flex-col overflow-hidden text-ink">`,
      `<div className="flex min-h-0 flex-1 flex-col overflow-hidden">`,
      `"page-shell relative flex min-h-0 flex-1 overflow-hidden",`,
      // The split form: layout classes and overflow in different arguments.
      `cn("flex min-h-0 flex-1 flex-col", scroll ? "overflow-y-auto" : "overflow-hidden", className)`,
    ];

    for (const line of shipped) expect(hiddenFrames(line)).toHaveLength(1);
  });

  it("does not flag a small box that clips for rounded corners", () => {
    const rounding = [
      `<div className="overflow-hidden rounded-card border border-line-subtle bg-surface-muted">`,
      `<div className="h-1.5 w-full overflow-hidden rounded-pill bg-brand-surface-hover">`,
    ];

    for (const line of rounding) expect(hiddenFrames(line)).toEqual([]);
  });
});
