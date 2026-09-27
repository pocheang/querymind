// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import { AdminThreatIntelPanel } from "@/pages/admin/AdminThreatIntelPanel";
import type { ThreatIntelSourceStatus } from "@/types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join(",")}` : key,
    i18n: { language: "en" },
  }),
}));

// Plain functions, not vi.fn: a rejecting vi.fn is reported as unhandled even
// when the component catches it (see DocumentItem.test.tsx).
const syncCalls: string[] = [];
let statusOutcome: () => Promise<{ sources: ThreatIntelSourceStatus[] }>;
let syncOutcome: () => Promise<unknown>;
vi.mock("@/lib/api", () => ({
  appApi: {
    adminThreatIntelStatus: () => statusOutcome(),
    adminThreatIntelSync: (source: string) => {
      syncCalls.push(source);
      return syncOutcome();
    },
  },
}));

const ROW = (overrides: Partial<ThreatIntelSourceStatus>): ThreatIntelSourceStatus => ({
  source: "kev",
  records: 1726,
  last_success: "2026-09-27T08:00:00+00:00",
  age_days: 0.5,
  stale_after_days: 7,
  state: "current",
  data_version: "2026.09.25",
  last_attempt_status: "succeeded",
  last_attempt_detail: "",
  ...overrides,
});

function missingRow(): never {
  throw new Error("the cell is not in a table row");
}

afterEach(() => cleanup());
beforeEach(() => {
  syncCalls.length = 0;
  statusOutcome = () =>
    Promise.resolve({
      sources: [
        ROW({ source: "nvd", records: 0, age_days: null, last_success: "", state: "empty", data_version: "" }),
        ROW({ source: "kev" }),
        ROW({
          source: "attack",
          state: "stale",
          age_days: 250,
          stale_after_days: 200,
          last_attempt_status: "failed",
          last_attempt_detail: "DownloadRefused: ceiling",
        }),
      ],
    });
  syncOutcome = () => Promise.resolve({ ok: true, status: "accepted", sources: [] });
});

describe("AdminThreatIntelPanel", () => {
  it("shows each source with its state, age and last attempt", async () => {
    render(<AdminThreatIntelPanel />);

    const kev = (await screen.findByText("kev")).closest("tr") ?? missingRow();
    expect(within(kev).getByText("admin.threatIntel.states.current")).toBeInTheDocument();
    expect(within(kev).getByText("admin.threatIntel.ageDays:0.5,7")).toBeInTheDocument();

    const nvd = screen.getByText("nvd").closest("tr") ?? missingRow();
    expect(within(nvd).getByText("admin.threatIntel.states.empty")).toBeInTheDocument();
    expect(within(nvd).getByText("admin.threatIntel.never")).toBeInTheDocument();

    const attack = screen.getByText("attack").closest("tr") ?? missingRow();
    expect(within(attack).getByText("admin.threatIntel.states.stale")).toBeInTheDocument();
    expect(within(attack).getByText(/failed: DownloadRefused: ceiling/)).toBeInTheDocument();
  });

  it("syncs one source from its row, or all of them", async () => {
    render(<AdminThreatIntelPanel />);

    const kev = (await screen.findByText("kev")).closest("tr") ?? missingRow();
    fireEvent.click(within(kev).getByRole("button", { name: "admin.threatIntel.sync" }));
    fireEvent.click(screen.getByRole("button", { name: "admin.threatIntel.syncAll" }));

    await waitFor(() => expect(syncCalls).toEqual(["kev", "all"]));
    expect(await screen.findByText("admin.threatIntel.queued")).toBeInTheDocument();
  });

  it("says so when a sync cannot be queued", async () => {
    syncOutcome = () => Promise.reject(new Error("503"));
    render(<AdminThreatIntelPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "admin.threatIntel.syncAll" }));

    expect(await screen.findByText("admin.threatIntel.syncFailed")).toBeInTheDocument();
  });

  it("says so when the status cannot be read", async () => {
    statusOutcome = () => Promise.reject(new Error("403"));
    render(<AdminThreatIntelPanel />);

    expect(await screen.findByText("admin.threatIntel.loadFailed")).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });
});
