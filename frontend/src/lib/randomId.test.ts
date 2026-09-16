import { afterEach, describe, expect, it, vi } from "vitest";

import { randomId } from "./randomId";

/**
 * The reason this exists at all: `crypto.randomUUID` is undefined outside a
 * secure context, and the production compose file publishes the frontend on
 * port 80. Reached over plain http from another machine, the old call threw
 * inside the chat run's try block and every question failed with a generic
 * "Request failed".
 *
 * The server validates the id it is given -- `AdvancedRAGRequest.execution_id`
 * is matched against a UUID pattern -- so the fallback has to produce a real
 * v4 UUID, not merely 32 random hex digits. That is the same pattern, asserted
 * here so the two cannot drift.
 */
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

const realCrypto = globalThis.crypto;

/** Replace Web Crypto with `overrides`, or remove it entirely for `null`. */
function withCrypto(overrides: Partial<Crypto> | null) {
  vi.stubGlobal("crypto", overrides === null ? undefined : { ...realCrypto, ...overrides });
}

afterEach(() => vi.unstubAllGlobals());

describe("randomId", () => {
  it("uses crypto.randomUUID when the context is secure enough to have it", () => {
    const randomUUID = vi.fn(() => "11111111-2222-4333-8444-555555555555");
    withCrypto({ randomUUID } as Partial<Crypto>);

    expect(randomId()).toBe("11111111-2222-4333-8444-555555555555");
    expect(randomUUID).toHaveBeenCalledTimes(1);
  });

  it("still returns a valid v4 UUID when randomUUID is missing", () => {
    // getRandomValues is NOT gated on a secure context, so this is the shape
    // of an http:// page: no randomUUID, real randomness still available.
    withCrypto({ randomUUID: undefined } as unknown as Partial<Crypto>);

    for (let i = 0; i < 50; i += 1) expect(randomId()).toMatch(UUID_V4);
  });

  it("sets the version and variant bits itself rather than passing bytes through", () => {
    // All-zero bytes would spell the nil UUID; the version nibble and the
    // variant bits have to be stamped on regardless of what the source gave.
    withCrypto({
      randomUUID: undefined,
      getRandomValues: ((array: Uint8Array) => array.fill(0)) as Crypto["getRandomValues"],
    } as unknown as Partial<Crypto>);

    expect(randomId()).toBe("00000000-0000-4000-8000-000000000000");
  });

  it("falls back to Math.random with no Web Crypto at all", () => {
    withCrypto(null);

    const ids = new Set(Array.from({ length: 50 }, () => randomId()));
    for (const id of ids) expect(id).toMatch(UUID_V4);
    expect(ids.size).toBe(50);
  });

  it("does not repeat itself", () => {
    const ids = new Set(Array.from({ length: 1000 }, () => randomId()));

    expect(ids.size).toBe(1000);
  });
});
