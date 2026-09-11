import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import en from "@/i18n/locales/en.json";
import zh from "@/i18n/locales/zh.json";

/**
 * A missing translation key does not fail anything.
 *
 * i18next returns the inline `defaultValue` when a key is absent, so a key the
 * locales never got renders the English string in the Chinese UI -- silently,
 * forever, in an application whose reason for existing is that it works in
 * Chinese. Thirteen keys were in that state on 2026-09-07, including all five
 * top-bar view names, "Sign in" and "Sign out".
 *
 * The other direction matters too: a key one locale has and the other does not
 * is a string that changes language when nothing else on the page does.
 */

const SRC = join(process.cwd(), "src");

function flatten(value: unknown, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    const key = `${prefix}${k}`;
    if (v && typeof v === "object" && !Array.isArray(v)) Object.assign(out, flatten(v, `${key}.`));
    else out[key] = String(v);
  }
  return out;
}

function sources(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) sources(full, acc);
    else if (/\.tsx?$/.test(entry) && !entry.includes(".test.")) acc.push(full);
  }
  return acc;
}

const EN = flatten(en);
const ZH = flatten(zh);

/** `t("a.b.c"` -- the literal-key calls, which are the ones a locale must hold. */
const asked = new Set<string>();
for (const file of sources(SRC)) {
  const text = readFileSync(file, "utf8");
  for (const m of text.matchAll(/\bt\(\s*"([a-zA-Z][\w.]*)"/g)) asked.add(m[1]);
}

describe("the locale files", () => {
  it("asks for at least a plausible number of keys", () => {
    // A guard on the guard: if the scan stops matching, every assertion below
    // passes vacuously, which is how a check quietly stops checking.
    expect(asked.size).toBeGreaterThan(200);
  });

  it("defines every key the app asks for, in English", () => {
    expect([...asked].filter((k) => !(k in EN)).sort((a, b) => a.localeCompare(b))).toEqual([]);
  });

  it("defines every key the app asks for, in Chinese", () => {
    expect([...asked].filter((k) => !(k in ZH)).sort((a, b) => a.localeCompare(b))).toEqual([]);
  });

  it("keeps the two locales on the same key set", () => {
    const onlyEn = Object.keys(EN).filter((k) => !(k in ZH)).sort((a, b) => a.localeCompare(b));
    const onlyZh = Object.keys(ZH).filter((k) => !(k in EN)).sort((a, b) => a.localeCompare(b));
    expect({ onlyEn, onlyZh }).toEqual({ onlyEn: [], onlyZh: [] });
  });

  it("leaves no Chinese value identical to its English one where it should differ", () => {
    // Proper nouns and codes legitimately match; a long sentence matching is a
    // key that was copied rather than translated.
    const copied = Object.keys(EN).filter(
      (k) => EN[k] === ZH[k] && EN[k].length > 24 && /\s/.test(EN[k]) && !/^https?:/.test(EN[k])
    );
    expect(copied).toEqual([]);
  });
});
