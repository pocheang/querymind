// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SettingsDrawer } from "@/components/SettingsDrawer";

/**
 * The drawer used to be a per-user model configuration form. Models are
 * configured by an administrator and applied to every user, so what is pinned
 * here is mostly what must NOT be here: any control that would take a provider,
 * a key or a model from a reader who cannot change one.
 *
 * A form here is not merely useless. The one that shipped collected a
 * third-party API key, encrypted it into the user's row, and returned a green
 * "connection succeeded" from a probe of the posted values -- so the promise
 * looked kept while every question the user asked went to the administrator's
 * model instead.
 */

vi.mock("react-i18next", () => ({
  // A fresh `t` per render on purpose: it is what react-i18next does on a
  // language change, and an effect keyed on `t` turns that into a refetch loop.
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join(",")}` : key,
    i18n: { language: "en" },
  }),
}));

vi.mock("@/features/integrations/IntegrationsPanel", () => ({
  IntegrationsPanel: () => <div data-testid="integrations" />,
}));

vi.mock("@/features/memory/MemoryPanel", () => ({
  MemoryPanel: () => <div data-testid="memory" />,
}));

const getActiveModel = vi.fn();
vi.mock("@/lib/api", () => ({
  appApi: {
    getActiveModel: () => getActiveModel(),
  },
}));

beforeEach(() => {
  getActiveModel.mockReset();
  getActiveModel.mockResolvedValue({
    ok: true,
    managed_by_admin: true,
    provider: "openai",
    model: "gpt-5.5",
  });
});

afterEach(() => cleanup());

describe("the settings drawer", () => {
  it("names the model an administrator chose, and says who chose it", async () => {
    render(<SettingsDrawer isOpen onClose={() => {}} />);

    expect(await screen.findByText("openai / gpt-5.5")).toBeInTheDocument();
    expect(screen.getByText("components.settings.managedByAdmin")).toBeInTheDocument();
  });

  it("offers no way to change it", async () => {
    render(<SettingsDrawer isOpen onClose={() => {}} />);
    await screen.findByText("openai / gpt-5.5");

    // No field of any kind: the retired form had a provider tab strip, an API
    // key box, a base URL, a model name, a temperature slider and a token count.
    expect(screen.queryAllByRole("textbox")).toHaveLength(0);
    expect(screen.queryAllByRole("combobox")).toHaveLength(0);
    expect(screen.queryAllByRole("slider")).toHaveLength(0);
    expect(screen.queryAllByRole("spinbutton")).toHaveLength(0);

    // The only button is the header's close control. A Save or a Test here
    // would be promising an effect this reader cannot have.
    const buttonNames = screen
      .getAllByRole("button")
      .map((node) => node.getAttribute("aria-label") || node.textContent || "");
    expect(buttonNames.every((name) => name.includes("components.settings.close"))).toBe(true);
  });

  it("says the deployment is answering when no administrator configuration is in effect", async () => {
    getActiveModel.mockResolvedValue({ ok: true, managed_by_admin: false, provider: "", model: "" });
    render(<SettingsDrawer isOpen onClose={() => {}} />);

    expect(await screen.findByText("components.settings.deploymentDefault")).toBeInTheDocument();
    expect(screen.queryByText("components.settings.modelUnavailable")).not.toBeInTheDocument();
  });

  it("distinguishes 'nothing is configured' from 'we could not ask'", async () => {
    getActiveModel.mockRejectedValue(new Error("network"));
    render(<SettingsDrawer isOpen onClose={() => {}} />);

    expect(await screen.findByText("components.settings.modelUnavailable")).toBeInTheDocument();
  });

  it("keeps integrations and memory when the model read fails", async () => {
    getActiveModel.mockRejectedValue(new Error("network"));
    render(<SettingsDrawer isOpen onClose={() => {}} />);

    // The read-only model line is a courtesy; these two are why the drawer opens.
    expect(await screen.findByTestId("integrations")).toBeInTheDocument();
    expect(screen.getByTestId("memory")).toBeInTheDocument();
  });

  it("reads the model once, not once per render", async () => {
    const { rerender } = render(<SettingsDrawer isOpen onClose={() => {}} />);
    await screen.findByText("openai / gpt-5.5");

    rerender(<SettingsDrawer isOpen onClose={() => {}} />);
    rerender(<SettingsDrawer isOpen onClose={() => {}} />);

    // Keyed on `isOpen`, never on `t`: the mock above hands back a new `t` every
    // render, which under an effect keyed on it is an unbounded refetch loop --
    // and the tell for that in this repository was three vitest workers reaching
    // several GB with no output at all.
    await waitFor(() => expect(getActiveModel).toHaveBeenCalledTimes(1));
  });

  it("renders nothing while closed", () => {
    const { container } = render(<SettingsDrawer isOpen={false} onClose={() => {}} />);

    expect(container).toBeEmptyDOMElement();
    expect(getActiveModel).not.toHaveBeenCalled();
  });
});
