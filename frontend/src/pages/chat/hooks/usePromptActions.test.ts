import { beforeEach, describe, expect, it, vi } from "vitest";

// A prompt reaches the page as written (CodeQL #1, #2). `sanitizeString`
// stripped `<`, `>`, `javascript:` and `on...=` from the checked prompt and from
// the title shown in the delete confirmation. Every one of those values is
// rendered as React text, which React escapes, so the filter bought no safety
// and cut words out of ordinary prompts.

const promptCheck = vi.fn();
const promptDelete = vi.fn();

vi.mock("@/lib/api", () => ({
  appApi: {
    promptCheck: (...args: unknown[]) => promptCheck(...args),
    promptDelete: (...args: unknown[]) => promptDelete(...args),
  },
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => (options ? `${key} ${JSON.stringify(options)}` : key),
  }),
}));

const { usePromptActions } = await import("./usePromptActions");

function params() {
  return {
    setPrompts: vi.fn(),
    setPromptsLoading: vi.fn(),
    setEditingPromptId: vi.fn(),
    setPromptTitle: vi.fn(),
    setPromptContent: vi.fn(),
    setPromptCheckInfo: vi.fn(),
    setAgentClassHint: vi.fn(),
    setError: vi.fn(),
    notify: vi.fn(),
    handleApiError: vi.fn(async () => {}),
    confirm: vi.fn(async (_opts: { message: string; title?: string; isDanger?: boolean }) => false),
  };
}

describe("usePromptActions keeps prompt text as written", () => {
  beforeEach(() => {
    promptCheck.mockReset();
    promptDelete.mockReset();
  });

  it("puts the checked prompt back unchanged", async () => {
    promptCheck.mockResolvedValue({
      title: "Compare <A> and <B>",
      content: "Why do browsers block javascript: URLs? Name button=submit.",
      suggestions: ["Say what <A> is"],
      issues: ["mentions onclick= without context"],
    });
    const p = params();

    await usePromptActions(p).checkPrompt("draft title", "draft content that is long enough", false);

    expect(p.setPromptTitle).toHaveBeenCalledWith("Compare <A> and <B>");
    const content = p.setPromptContent.mock.calls[0][0] as string;
    expect(content).toContain("javascript: URLs");
    expect(content).toContain("button=submit");
    expect(content).toContain("Say what <A> is");
    expect(p.setPromptCheckInfo.mock.calls.at(-1)?.[0]).toContain("onclick=");
  });

  it("shows the real title in the delete confirmation", async () => {
    const p = params();

    await usePromptActions(p).deletePrompt({ prompt_id: "p1", title: "Compare <A> and <B>" } as never, null);

    expect(p.confirm).toHaveBeenCalledTimes(1);
    expect(p.confirm.mock.calls[0][0].message).toContain("Compare <A> and <B>");
    expect(promptDelete).not.toHaveBeenCalled();
  });
});
