import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api-client";
import { shouldForgetSession } from "@/lib/sessionRecovery";

/**
 * A backend that is briefly unreachable must not sign anybody out.
 *
 * `App`'s bootstrap called `/auth/me` and cleared the token on any rejection.
 * Reproduced on 2026-09-09 by restarting the API under an open tab: the token
 * was gone from `localStorage` afterwards and the password had to be typed
 * again -- for an outage that lasted seconds and said nothing about whether
 * the session was still valid.
 *
 * The rule lives in its own function so it can be asserted in both directions.
 * Inside the `.catch()` it was reachable only by rendering the whole app, which
 * is why "any error means sign out" survived: nothing could state it.
 */
describe("what may destroy a stored session", () => {
  it("forgets the session when the server says the token is no longer valid", () => {
    expect(shouldForgetSession(new ApiError(401, "unauthorized"))).toBe(true);
  });

  it.each([
    ["a backend that is restarting", new ApiError(500, "Internal Server Error")],
    ["a gateway with nothing behind it", new ApiError(502, "Bad Gateway")],
    ["a request that timed out", new ApiError(408, "Request timed out")],
    ["an unreachable server", new TypeError("Failed to fetch")],
    ["an aborted request", new DOMException("aborted", "AbortError")],
    ["something that is not an error at all", "boom"],
  ])("keeps it through %s", (_label, error) => {
    expect(shouldForgetSession(error)).toBe(false);
  });

  it("does not forget on 403, which is about the resource and not the session", () => {
    // A permission the account lacks is not a reason to end the session; the
    // user is still who they said they were.
    expect(shouldForgetSession(new ApiError(403, "forbidden"))).toBe(false);
  });
});
