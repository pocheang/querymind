// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi, beforeEach } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import { TopNavMetrics } from "@/components/layout/TopNavMetrics";
import { analyticsApi } from "@/services/api/app";

/**
 * The readout must be absent rather than wrong.
 *
 * `RetrievalLogger` answers an empty log with `avg_total_time_ms: 0,
 * success_rate: 0`, which renders as "Success: 0.0%" in warning amber -- a top
 * bar telling every reader on every page that the system is failing, when what
 * it means is that nobody has asked it anything. The check is on the sample
 * count for exactly that reason.
 */

const overview = (patch: Record<string, unknown> = {}) => ({
  total_queries: 42,
  success_rate: 0.98,
  avg_retrieval_time_ms: 120,
  avg_total_time_ms: 1840,
  avg_retrieved_count: 4,
  agent_distribution: {},
  route_distribution: {},
  ...patch,
});

beforeEach(() => vi.restoreAllMocks());
afterEach(cleanup);

describe("the top bar readout", () => {
  it("shows the numbers once there are samples", async () => {
    vi.spyOn(analyticsApi, "overview").mockResolvedValue(overview() as never);
    render(<TopNavMetrics />);
    await waitFor(() => expect(screen.getByText("1840ms")).toBeTruthy());
    expect(screen.getByText("98.0%")).toBeTruthy();
  });

  it("renders nothing when no query has been logged", async () => {
    vi.spyOn(analyticsApi, "overview").mockResolvedValue(
      overview({ total_queries: 0, success_rate: 0, avg_total_time_ms: 0 }) as never
    );
    const { container } = render(<TopNavMetrics />);
    await waitFor(() => expect(analyticsApi.overview).toHaveBeenCalled());
    expect(container.innerHTML).toBe("");
  });

  it("renders nothing, and does not throw, when the endpoint fails", async () => {
    vi.spyOn(analyticsApi, "overview").mockRejectedValue(new Error("403"));
    const { container } = render(<TopNavMetrics />);
    await waitFor(() => expect(analyticsApi.overview).toHaveBeenCalled());
    expect(container.innerHTML).toBe("");
  });
});
