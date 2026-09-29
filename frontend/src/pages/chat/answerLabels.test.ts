import { describe, expect, it } from "vitest";

import en from "@/i18n/locales/en.json";
import zh from "@/i18n/locales/zh.json";
import { ANSWER_SHAPES, TOOL_IDS, answerShapeKey, toolNameKey } from "./answerLabels";

/**
 * The keys `answerLabels.ts` derives are invisible to `i18n/locales.test.ts`,
 * which only sees literal `t("...")` calls, so this is where a missing entry is
 * caught -- otherwise it would render the raw key forever with nothing
 * reporting it.
 */

function lookup(locale: unknown, key: string): unknown {
  return key.split(".").reduce<unknown>((node, part) => {
    return typeof node === "object" && node !== null ? (node as Record<string, unknown>)[part] : undefined;
  }, locale);
}

const KEYS = [...ANSWER_SHAPES.map(answerShapeKey), ...TOOL_IDS.map(toolNameKey)];

describe("derived answer-shape and tool keys", () => {
  it("derive the key the locales use", () => {
    expect(answerShapeKey("vulnerability_exposure_assessment")).toBe("answerShapes.vulnerabilityExposureAssessment");
    expect(toolNameKey("querymind_cyber_cve_lookup")).toBe("toolNames.cyberCveLookup");
  });

  it.each(KEYS)("%s is a string in English and in Chinese", (key) => {
    expect(typeof lookup(en, key)).toBe("string");
    expect(typeof lookup(zh, key)).toBe("string");
  });

  it.each(KEYS)("%s is translated rather than copied", (key) => {
    expect(lookup(zh, key)).not.toBe(lookup(en, key));
  });
});
