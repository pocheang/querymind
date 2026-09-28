// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { DocumentItem } from "@/pages/chat/components/DocumentItem";
import { AGENT_MODES } from "@/pages/chat/constants";
import type { IndexedFileSummary } from "@/types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: unknown) => (typeof fallback === "string" ? fallback : key),
    i18n: { language: "en" },
  }),
}));

// Calls are recorded in a plain array and the outcome is a plain function: a
// rejecting `vi.fn` implementation is reported by vitest as an unhandled
// rejection even when the component awaits it inside try/catch.
const relabelCalls: Array<[string, string]> = [];
let relabelOutcome: () => Promise<{ document_id: string; agent_class: string }> = () =>
  Promise.resolve({ document_id: "doc-1", agent_class: "general" });
vi.mock("@/lib/api", () => ({
  appApi: {
    documentRelabel: (id: string, agentClass: string) => {
      relabelCalls.push([id, agentClass]);
      return relabelOutcome();
    },
  },
}));

afterEach(() => cleanup());
beforeEach(() => {
  relabelCalls.length = 0;
});

const DOC: IndexedFileSummary = {
  filename: "runbook.md",
  source: "/uploads/alice/runbook.md",
  chunks: 3,
  document_id: "doc-1",
  agent_class: "general",
  can_manage: true,
};

function renderItem(doc: IndexedFileSummary = DOC) {
  return render(
    <DocumentItem
      doc={doc}
      canUploadAndManageDocs
      isAdmin={false}
      currentUserId="alice"
      onReindexDocument={vi.fn()}
      onDeleteDocument={vi.fn()}
    />
  );
}

describe("DocumentItem domain label", () => {
  it("offers exactly the mode cards' classes, without the Auto entry", () => {
    renderItem();

    const select = screen.getByRole("combobox", { name: "components.workbench.domainLabel" });
    const values = Array.from(select.querySelectorAll("option")).map((option) => option.getAttribute("value"));
    expect(values).toEqual(AGENT_MODES.filter((mode) => mode.key).map((mode) => mode.key));
    expect(select).toHaveValue("general");
  });

  it("saves a new label by document id", async () => {
    relabelOutcome = () => Promise.resolve({ document_id: "doc-1", agent_class: "cybersecurity" });
    renderItem();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "cybersecurity" } });

    await waitFor(() => expect(relabelCalls).toEqual([["doc-1", "cybersecurity"]]));
    await waitFor(() => expect(screen.getByRole("combobox")).not.toBeDisabled());
    expect(screen.getByRole("combobox")).toHaveValue("cybersecurity");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("puts the old label back and says so when saving fails", async () => {
    relabelOutcome = () => Promise.reject(new Error("403"));
    renderItem();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "cybersecurity" } });

    expect(await screen.findByRole("alert")).toHaveTextContent("components.workbench.relabelFailed");
    expect(screen.getByRole("combobox")).toHaveValue("general");
  });

  it("is not offered on a row the caller cannot manage", () => {
    renderItem({ ...DOC, can_manage: false });

    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("is not offered on a row with no document id to address", () => {
    renderItem({ ...DOC, document_id: null });

    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("keeps a label the cards do not know, rather than silently showing another", () => {
    renderItem({ ...DOC, agent_class: "policy" });

    expect(screen.getByRole("combobox")).toHaveValue("policy");
  });
});
