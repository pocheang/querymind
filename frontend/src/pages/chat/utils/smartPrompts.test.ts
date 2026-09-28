import { describe, expect, it } from "vitest";

import { AGENT_MODES } from "@/pages/chat/constants";
import type { SessionMessage } from "@/types/api";
import { generateSmartPrompts, starterPrompts } from "./smartPrompts";

const CLASS_NAMES = AGENT_MODES.map((mode) => mode.key).filter(Boolean);

describe("starter prompts", () => {
  it("offer the selected specialist's own questions", () => {
    expect(starterPrompts("cybersecurity", true)[0]).toContain("log4j 2.14.1");
    expect(starterPrompts("data_analysis", false)[0]).toMatch(/sales table/);
  });

  it("show one question per specialist under Auto Router", () => {
    const prompts = starterPrompts("", true);

    expect(prompts).toHaveLength(4);
    expect(new Set(prompts).size).toBe(4);
  });

  it("never name an internal class, which the old starters asked the reader to type", () => {
    for (const hint of ["", ...CLASS_NAMES]) {
      for (const prompt of [...starterPrompts(hint, true), ...starterPrompts(hint, false)]) {
        for (const name of CLASS_NAMES) expect(prompt).not.toContain(name);
      }
    }
  });

  it("are what an empty conversation gets", () => {
    expect(generateSmartPrompts([], true, "compliance")).toEqual(starterPrompts("compliance", true));
  });
});

describe("follow-up prompts", () => {
  it("follow the specialist that answered, now that the answer names it", () => {
    const messages: SessionMessage[] = [
      { message_id: "u", role: "user", content: "log4j 2.14.1 受影响吗" },
      { message_id: "a", role: "assistant", content: "受影响", metadata: { agent_class: "cybersecurity" } },
    ];

    expect(generateSmartPrompts(messages, true)[0]).toContain("KEV");
  });
});
