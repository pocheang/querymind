/**
 * A random UUID that does not need a secure context.
 *
 * `crypto.randomUUID` is only defined in a secure context -- HTTPS, or
 * localhost. `deploy/compose/compose.production.yaml` publishes the frontend
 * on port 80, so a deployment reached over plain http from another machine
 * (the ordinary case for an internal tool on a LAN) has no `randomUUID` at
 * all, and calling it throws a TypeError rather than degrading.
 *
 * That was survivable while the only callers minted toast ids. It stopped
 * being survivable when the chat run began generating its own execution id
 * before sending the query: the throw happens inside `runQueryAndStream`'s
 * try, so every question on such a deployment would have failed with a
 * generic "Request failed" naming nothing.
 *
 * `crypto.getRandomValues` is NOT gated on a secure context, so the fallback
 * is still cryptographic-quality randomness -- it only has to set the version
 * and variant bits itself. `Math.random` is the last resort for an
 * environment with no Web Crypto at all; these ids name a local trace and a
 * toast, not a secret, so a weaker source is better than a thrown error.
 */
export function randomId(): string {
  const webCrypto = globalThis.crypto;
  if (typeof webCrypto?.randomUUID === "function") return webCrypto.randomUUID();

  const bytes = new Uint8Array(16);
  if (typeof webCrypto?.getRandomValues === "function") {
    webCrypto.getRandomValues(bytes);
  } else {
    // Non-cryptographic fallback only for environments lacking Web Crypto (e.g. test mocks); these IDs name local traces/toasts, not secrets.
    for (let i = 0; i < bytes.length; i += 1) bytes[i] = Math.floor(Math.random() * 256); // NOSONAR
  }

  // RFC 4122 4.4: version 4 in the high nibble of byte 6, variant 10 in the
  // top two bits of byte 8. The server validates this shape --
  // AdvancedRAGRequest.execution_id is matched against a UUID pattern -- so a
  // fallback that produced 32 arbitrary hex digits would be rejected as a
  // 422, which is a harder failure to read than the one being fixed.
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
