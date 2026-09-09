// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { IntegrationsPanel } from "@/features/integrations/IntegrationsPanel";
import type { ConnectorView } from "@/features/integrations/api";

/**
 * The panel had no test at all, and was rewritten because it had no styling
 * either: it carried `integrations-panel` and `runtime-panel-empty`, two class
 * names whose stylesheets were deleted in the 2026-09-07 purge, so every field
 * and list rendered as a browser default inside a finished drawer. Nothing
 * reported that -- a class name matching no rule is invisible to lint, to
 * types and to tests -- so what is pinned here is the behaviour instead, plus
 * the one thing a class list can check.
 */

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join(",")}` : key,
    i18n: { language: "en" },
  }),
}));

const listConnectors = vi.fn();
const createConnector = vi.fn();
const setConnectorEnabled = vi.fn();
const testConnector = vi.fn();
const deleteConnector = vi.fn();
vi.mock("@/features/integrations/api", () => ({
  listConnectors: (signal?: AbortSignal) => listConnectors(signal),
  createConnector: (input: unknown) => createConnector(input),
  setConnectorEnabled: (id: string, enabled: boolean) => setConnectorEnabled(id, enabled),
  testConnector: (id: string) => testConnector(id),
  deleteConnector: (id: string) => deleteConnector(id),
}));

function connector(overrides: Partial<ConnectorView> = {}): ConnectorView {
  return {
    connector_id: "atlas_ci",
    name: "Atlas CI",
    base_url: "https://ci.internal",
    allowed_hosts: ["ci.internal"],
    status: "enabled",
    test_status: "passed",
    ...overrides,
  };
}

const TWO = [
  connector(),
  connector({ connector_id: "ticket_desk", name: "Ticket desk", status: "disabled", test_status: "failed" }),
];

beforeEach(() => {
  listConnectors.mockReset().mockResolvedValue(TWO);
  createConnector.mockReset();
  setConnectorEnabled.mockReset().mockResolvedValue(connector({ status: "disabled" }));
  testConnector.mockReset().mockResolvedValue({ status: "passed", message: "reachable" });
  deleteConnector.mockReset().mockResolvedValue(undefined);
});

afterEach(cleanup);

describe("the integrations panel", () => {
  it("lists every connector with its status", async () => {
    render(<IntegrationsPanel />);

    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));
    expect(screen.getByText("Atlas CI")).toBeInTheDocument();
    expect(screen.getByText("features.integrations.status.enabled")).toBeInTheDocument();
    expect(screen.getByText("features.integrations.status.disabled")).toBeInTheDocument();
  });

  it("does not report an empty list when the request failed", async () => {
    // "You have no integrations" and "we could not ask" must not look alike.
    listConnectors.mockRejectedValue(new Error("gateway is down"));
    render(<IntegrationsPanel />);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("gateway is down"));
    expect(screen.queryByText("features.integrations.empty")).toBeNull();
  });

  it("toggles a connector through the API", async () => {
    render(<IntegrationsPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));

    await userEvent.click(screen.getByRole("button", { name: "features.integrations.disable" }));

    expect(setConnectorEnabled).toHaveBeenCalledWith("atlas_ci", false);
  });

  it("will not test a connector that is switched off", async () => {
    // The backend refuses it; offering the button anyway teaches a wrong model
    // of what the control does.
    render(<IntegrationsPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));

    const buttons = screen.getAllByRole("button", { name: "features.integrations.test" });

    expect(buttons[0]).toBeEnabled();
    expect(buttons[1]).toBeDisabled();
  });

  it("hides the list markers rather than relying on the row being a flexbox", async () => {
    // The rows carried browser bullets until this: the sibling memory panel
    // escapes them only because its `<li>` happens to be `display: flex`, which
    // is incidental and silently reappears the day a row becomes a block.
    render(<IntegrationsPanel />);

    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));
    expect(screen.getByRole("list").className.split(" ")).toContain("list-none");
  });

  it("labels every field of the connect form", async () => {
    // Each input is reached by its accessible name, so a `<label htmlFor>` that
    // stops matching its input fails here rather than only for a screen reader.
    render(<IntegrationsPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));

    for (const label of [
      "features.integrations.integrationId",
      "features.integrations.name",
      "features.integrations.baseUrl",
      "features.integrations.allowedHosts",
      "features.integrations.accessSecret",
    ]) {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    }
  });

  it("asks before destroying a connector, then removes it from the list", async () => {
    // Deleting is not disabling: it destroys a third-party secret the server
    // cannot show back, and there was no way to do it at all until 2026-09-09.
    render(<IntegrationsPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));

    await userEvent.click(
      screen.getByRole("button", { name: "features.integrations.removeNamed:Atlas CI" })
    );

    expect(deleteConnector).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "features.integrations.remove" }));

    expect(deleteConnector).toHaveBeenCalledWith("atlas_ci");
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(1));
    expect(screen.queryByText("Atlas CI")).toBeNull();
  });

  it("destroys nothing when the confirmation is declined", async () => {
    // The half worth pinning: an irreversible action that fires anyway makes
    // the dialog decoration.
    render(<IntegrationsPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));

    await userEvent.click(
      screen.getByRole("button", { name: "features.integrations.removeNamed:Atlas CI" })
    );
    await userEvent.click(screen.getByRole("button", { name: "common.cancel" }));

    expect(deleteConnector).not.toHaveBeenCalled();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });

  it("sends the trimmed form and splits the host list", async () => {
    createConnector.mockResolvedValue(connector({ connector_id: "wiki", name: "Wiki" }));
    render(<IntegrationsPanel />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));

    // The id is typed clean on purpose. `pattern="[a-z][a-z0-9_-]{0,63}"` is
    // implicitly anchored, so a padded id fails constraint validation and the
    // form never submits -- the handler's `.trim()` never runs for that field.
    // That is the right behaviour (the browser says why), and asserting the
    // trim on the id would have been asserting something unreachable.
    await userEvent.type(screen.getByLabelText("features.integrations.integrationId"), "wiki");
    await userEvent.type(screen.getByLabelText("features.integrations.name"), " Wiki ");
    await userEvent.type(screen.getByLabelText("features.integrations.baseUrl"), "https://wiki.internal");
    await userEvent.type(screen.getByLabelText("features.integrations.allowedHosts"), "a.internal, b.internal ,");
    await userEvent.type(screen.getByLabelText("features.integrations.accessSecret"), "s3cret");
    await userEvent.click(screen.getByRole("button", { name: "features.integrations.addConnector" }));

    expect(createConnector).toHaveBeenCalledWith({
      connector_id: "wiki",
      name: "Wiki",
      base_url: "https://wiki.internal",
      allowed_hosts: ["a.internal", "b.internal"],
      secret: "s3cret",
    });
  });
});
