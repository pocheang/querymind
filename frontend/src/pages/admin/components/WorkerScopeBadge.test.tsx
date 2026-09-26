// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkerScopeBadge } from "@/pages/admin/components/AdminPrimitives";

/**
 * With several workers, the runtime panel, the overview's request figures and
 * the system log are each one process's slice (ARC-01 phase 8). The badge is
 * what stops a slice reading as the whole deployment, so it has to name the
 * pid it was given -- and say nothing at all when there is no worker to name,
 * rather than a placeholder that looks like one.
 */

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join(",")}` : key,
  }),
}));

afterEach(cleanup);

describe("WorkerScopeBadge", () => {
  it("names the worker's pid and explains itself with the host", () => {
    render(<WorkerScopeBadge worker={{ pid: 4242, host: "backend-1" }} />);

    const badge = screen.getByText("admin.worker.badge:4242");
    expect(badge).toHaveAttribute("title", "admin.worker.hint:backend-1");
  });

  it("renders nothing when the response named no worker", () => {
    const { container } = render(<WorkerScopeBadge worker={null} />);

    expect(container).toBeEmptyDOMElement();
  });
});
