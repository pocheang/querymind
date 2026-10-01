import { describe, expect, it } from "vitest";

import { imageSourceHost, isLoadableImageSource } from "@/lib/imageSource";

const ORIGIN = "https://querymind.example";

describe("isLoadableImageSource (SEC-09)", () => {
  it.each([
    "/api/v1/documents/by-id/d1/image",
    "assets/logo.png",
    `${ORIGIN}/assets/a.png`,
    "data:image/png;base64,iVBORw0KGgo=",
    "blob:https://querymind.example/0f1e",
  ])("loads %s", (src) => {
    expect(isLoadableImageSource(src, ORIGIN)).toBe(true);
  });

  it.each([
    "https://attacker.example/?q=secret",
    "http://querymind.example/a.png",
    "//attacker.example/x.png",
    "https://querymind.example.attacker.example/x.png",
    "javascript:alert(1)",
    "data:text/html,<script>1</script>",
    "",
    undefined,
  ])("does not load %s", (src) => {
    expect(isLoadableImageSource(src, ORIGIN)).toBe(false);
  });

  it("names the host it refused", () => {
    expect(imageSourceHost("https://attacker.example/?q=secret", ORIGIN)).toBe("attacker.example");
  });
});
