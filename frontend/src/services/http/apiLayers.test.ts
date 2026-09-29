import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// The HTTP client lives in services/http. lib/ once held re-export shims of it
// (api-client, admin-api), so one function had two or three import paths and a
// refactor could miss one. Only the app-level facade `lib/api.ts` remains.
describe("api layers", () => {
  it.each(["lib/api-client.ts", "lib/admin-api.ts", "lib/api-helpers.ts", "lib/api-error-handler.ts"])(
    "%s stays deleted",
    (file) => {
      expect(existsSync(resolve(__dirname, "../..", file))).toBe(false);
    }
  );
});
