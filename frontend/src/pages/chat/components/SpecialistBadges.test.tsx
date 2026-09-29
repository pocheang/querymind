// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import zh from "@/i18n/locales/zh.json";
import { MessageCard } from "@/pages/chat/components/MessageCard";
import { MetadataBadges } from "@/pages/chat/components/MetadataBadges";
import type { SessionMessage } from "@/types/api";

/**
 * An answer says which specialist wrote it, in what shape, and which tool each
 * [T{k}] in its text points at -- in the reader's language. Rendered against
 * the real Chinese locale, so a key missing from it fails here rather than
 * showing an identifier.
 */

function lookup(key: string): string | undefined {
  let node: unknown = zh;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null) return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === "string" ? node : undefined;
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: unknown) => lookup(key) ?? (typeof fallback === "string" ? fallback : key),
    i18n: { language: "zh" },
  }),
}));

afterEach(() => cleanup());

describe("the specialist badge", () => {
  it("names the specialist and the answer shape instead of the raw class", () => {
    render(<MetadataBadges metadata={{ agent_class: "cybersecurity", skill: "vulnerability_exposure_assessment" }} />);

    expect(screen.getByText("网络安全 · 漏洞暴露评估")).toBeInTheDocument();
    expect(screen.queryByText(/agent:/)).not.toBeInTheDocument();
  });

  it("stays quiet for the general analyst answering in the default shape", () => {
    render(<MetadataBadges metadata={{ agent_class: "general", skill: "answer_with_citations" }} />);

    expect(screen.queryByText(/综合分析/)).not.toBeInTheDocument();
  });

  it("still names a general answer that took a shape of its own", () => {
    render(<MetadataBadges metadata={{ agent_class: "general", skill: "timeline_builder" }} />);

    expect(screen.getByText("综合分析 · 时间线")).toBeInTheDocument();
  });

  it("falls back to the identifier for a class no card describes", () => {
    render(<MetadataBadges metadata={{ agent_class: "legal_review", skill: "" }} />);

    expect(screen.getByText("legal_review")).toBeInTheDocument();
  });
});

describe("the tool panel", () => {
  const message: SessionMessage = {
    message_id: "m1",
    role: "assistant",
    content: "受影响 [T1]。",
    metadata: {
      tool_runs: [
        { tool_id: "querymind_cyber_product_exposure", status: "succeeded", summary: "CVE-2021-44228", marker: "T1" },
        { tool_id: "querymind_cyber_cve_lookup", status: "succeeded", summary: "CVSS 10.0" },
      ],
    },
  };

  it("shows each tool by name and keeps the id for anyone who needs it", () => {
    render(<MessageCard message={message} onEditMessage={async () => {}} onRemoveMessage={async () => {}} />);

    const exposure = screen.getByText("产品暴露面");
    expect(exposure).toHaveAttribute("title", "querymind_cyber_product_exposure");
    expect(screen.getByText("CVE 查询")).toBeInTheDocument();
  });

  it("numbers only the tool the answer cites, with the number the answer uses", () => {
    render(<MessageCard message={message} onEditMessage={async () => {}} onRemoveMessage={async () => {}} />);

    expect(screen.getAllByText("T1")).toHaveLength(1);
    expect(screen.queryByText("T2")).not.toBeInTheDocument();
  });
});
