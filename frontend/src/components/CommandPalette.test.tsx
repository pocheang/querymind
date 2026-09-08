// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CommandPalette } from "@/components/CommandPalette";
import { useChatStore } from "@/stores/useChatStore";
import type { UserIdentity } from "@/types/auth";

/**
 * The palette's job is to be the one place every action is reachable from, so
 * what is worth pinning is which actions it OFFERS -- an entry that silently
 * stops rendering is the failure mode, and it looks like nothing.
 *
 * Note that vitest runs without `globals` here, so cleanup is explicit; a
 * missing `cleanup()` makes every later query in the file find two of
 * everything.
 */

// cmdk measures its list with a ResizeObserver, which jsdom does not
// implement. Stubbing it is not papering over a defect: the observer drives
// scroll-into-view for the selected row, and none of these assertions is about
// scrolling.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
Element.prototype.scrollIntoView ??= () => {};

const admin: UserIdentity = { user_id: "u1", username: "root", role: "admin" } as UserIdentity;
const viewer: UserIdentity = { user_id: "u2", username: "vera", role: "viewer" } as UserIdentity;

function show(props: Partial<React.ComponentProps<typeof CommandPalette>> = {}) {
  return render(
    <MemoryRouter initialEntries={["/app"]}>
      <CommandPalette open onOpenChange={vi.fn()} user={admin} {...props} />
    </MemoryRouter>
  );
}

afterEach(() => {
  cleanup();
  useChatStore.getState().reset();
});

describe("the command palette", () => {
  it("renders nothing while closed", () => {
    const { container } = render(
      <MemoryRouter>
        <CommandPalette open={false} onOpenChange={vi.fn()} user={admin} />
      </MemoryRouter>
    );
    expect(container.innerHTML).toBe("");
  });

  it("offers every view the user may reach", () => {
    show();
    for (const label of ["Operations Deck", "Analytics", "Admin Console", "Architecture", "Showcase"]) {
      expect(screen.getByText(label)).toBeTruthy();
    }
  });

  it("hides the views a role may not reach", () => {
    show({ user: viewer });
    expect(screen.queryByText("Admin Console")).toBeNull();
    expect(screen.getByText("Architecture")).toBeTruthy();
  });

  it("offers an action only when the route supplied its handler", () => {
    // The settings and session drawers belong to the chat page; on a route
    // that does not pass them the entry must be absent rather than inert.
    show();
    expect(screen.queryByText("Settings")).toBeNull();

    cleanup();
    show({ onOpenSettings: vi.fn() });
    expect(screen.getByText("Settings")).toBeTruthy();
  });

  it("runs the action and closes, in that order", async () => {
    const onOpenChange = vi.fn();
    const onNewSession = vi.fn();
    show({ onOpenChange, onNewSession });

    screen.getByText("New session").click();
    expect(onNewSession).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("lists sessions only once the app has loaded some", () => {
    show();
    expect(screen.queryByText("Sessions")).toBeNull();

    cleanup();
    useChatStore.getState().setSessions([
      { session_id: "s1", title: "Retrieval tuning" },
      { session_id: "s2", title: "Graph route" },
    ] as never);
    show();
    expect(screen.getByText("Retrieval tuning")).toBeTruthy();
  });

  it("shows nothing signed out beyond the public views", () => {
    show({ user: null, onOpenSettings: vi.fn(), onLogout: vi.fn() });
    expect(screen.queryByText("Sign out")).toBeNull();
    expect(screen.queryByText("Operations Deck")).toBeNull();
    expect(screen.getByText("Showcase")).toBeTruthy();
  });
});

describe("dismissal", () => {
  it("closes on Escape", () => {
    // cmdk's bare `Command` does not handle Escape -- the string does not
    // appear in its bundle -- so an overlay opened with ⌘K could only be
    // closed with a mouse until `useDismissable` landed.
    const onOpenChange = vi.fn();
    show({ onOpenChange });
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("gives focus back to whatever opened it", () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    expect(document.activeElement).toBe(opener);

    const { rerender } = render(
      <MemoryRouter initialEntries={["/app"]}>
        <CommandPalette open onOpenChange={vi.fn()} user={admin} />
      </MemoryRouter>
    );
    // The palette autofocuses its input, so focus has definitely moved.
    expect(document.activeElement).not.toBe(opener);

    rerender(
      <MemoryRouter initialEntries={["/app"]}>
        <CommandPalette open={false} onOpenChange={vi.fn()} user={admin} />
      </MemoryRouter>
    );
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });
});
