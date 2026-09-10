/* WCAG 1.4.3 audit over the live DOM -- second version.
 *
 * The first version's four traps all made it report a PASS (or a FAILURE) it
 * had not earned. Two more turned up once the admin console moved onto
 * `glass-card`, and both are fixed here:
 *
 *  5. THE AURORA IS A GRADIENT, SO EVERYTHING ON IT WAS SKIPPED. `glass-card`
 *     is `rgba(255,255,255,0.98)` -- alpha under 1, so the walk continues past
 *     it, reaches `body`, finds a `background-image` and bails. That made the
 *     whole console unmeasurable the moment it adopted the design's surface.
 *     The aurora is now RESOLVED: each pool is
 *     `radial-gradient(circle at X% Y%, C 0%, transparent N%)`, CSS sizes an
 *     unqualified circle farthest-corner, and alpha falls linearly to the N%
 *     stop -- so the four can be evaluated over a grid and the darkest real
 *     pixel used as the base. Compositing all four at full alpha instead (the
 *     first attempt) gives rgb(251,216,142), which no pixel on the page has,
 *     and reports --text-muted at 4.05 against a real 4.74. A worst case that
 *     cannot occur produces work that did not need doing.
 *     A gradient that is NOT the page ground still bails, and is listed.
 *
 *  6. A NON-PAINTING TAB NEVER SETTLES A TRANSITION, and waiting does not
 *     help. The tab pills read rgb(152,147,144) -- between white and
 *     --text-muted, set by no rule -- through a nine-second wait and a forced
 *     paint. `settle()` disables transitions and animations for the duration
 *     of the audit, so every element computes the value a reader sees.
 *
 * Before believing a pass, `probe()` plants three known-bad nodes (plain, a
 * color-mix tint of its own colour, and one dimmed only by an ancestor's
 * opacity) and asserts all three are reported.
 */
(() => {
  const parse = (s) => {
    if (!s || s === "transparent") return null;
    let m = /^rgba?\(([^)]+)\)$/.exec(s);
    if (m) {
      const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    }
    m = /^color\(srgb\s+([^)\s][^)]*)\)$/.exec(s); // what color-mix() computes to
    if (m) {
      const p = m[1].split(/[\s/]+/).filter(Boolean).map(Number);
      return { r: p[0] * 255, g: p[1] * 255, b: p[2] * 255, a: p.length > 3 ? p[3] : 1 };
    }
    return null;
  };
  const over = (f, b) => ({ r: f.r * f.a + b.r * (1 - f.a), g: f.g * f.a + b.g * (1 - f.a), b: f.b * f.a + b.b * (1 - f.a), a: 1 });
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  const ratio = (a, b) => { const x = L(a), y = L(b), hi = Math.max(x, y), lo = Math.min(x, y); return (hi + 0.05) / (lo + 0.05); };

  const hex = (s) => { const h = s.trim().replace("#", ""); return { r: Number.parseInt(h.slice(0, 2), 16), g: Number.parseInt(h.slice(2, 4), 16), b: Number.parseInt(h.slice(4, 6), 16), a: 1 }; };

  /** The aurora's composited colour at one pixel: each pool's alpha falls
   *  linearly from its centre to its radius, over the page ground. */
  const compositeAuroraAt = (x, y, pools, page) => {
    let c = { ...page };
    for (const p of pools) {
      if (!p.c) continue;
      const d = Math.hypot(x - p.cx, y - p.cy);
      const t = d >= p.r ? 0 : 1 - d / p.r;
      if (t > 0) c = over({ ...p.c, a: p.c.a * t }, c);
    }
    return c;
  };

  /** The darkest pixel the aurora actually paints, at this viewport. */
  const auroraDarkest = () => {
    const cs = getComputedStyle(document.documentElement);
    const W = window.innerWidth, H = window.innerHeight;
    const page = hex(cs.getPropertyValue("--bg-page"));
    const pools = [
      [0.82, 0.76, 0.38, "--aurora-4"],
      [0.5, 0.9, 0.5, "--aurora-3"],
      [0.9, 0.15, 0.42, "--aurora-2"],
      [0.1, 0.12, 0.45, "--aurora-1"],
    ].map(([px, py, end, tok]) => {
      const cx = px * W, cy = py * H;
      const far = Math.max(Math.hypot(cx, cy), Math.hypot(cx - W, cy), Math.hypot(cx, cy - H), Math.hypot(cx - W, cy - H));
      return { cx, cy, r: end * far, c: parse(cs.getPropertyValue(tok).trim()) };
    });
    let worst = page, worstL = Infinity;
    for (let y = 0; y <= H; y += 8) {
      for (let x = 0; x <= W; x += 8) {
        const c = compositeAuroraAt(x, y, pools, page);
        const l = L(c);
        if (l < worstL) { worstL = l; worst = c; }
      }
    }
    return worst;
  };

  const settle = () => {
    let s = document.getElementById("__audit-settle");
    if (!s) {
      s = document.createElement("style");
      s.id = "__audit-settle";
      s.textContent = "*,*::before,*::after{transition:none!important;animation:none!important}";
      document.head.appendChild(s);
    }
    document.body.getBoundingClientRect();
  };

  const SKIP = new Set(["SCRIPT", "STYLE", "SVG", "PATH", "NOSCRIPT", "TITLE"]);

  const elementOpacity = (el) => { let o = 1, n = el; while (n?.nodeType === 1) { const v = Number.parseFloat(getComputedStyle(n).opacity); if (!Number.isNaN(v)) { o *= v; } n = n.parentElement; } return o; };

  const backdropColor = (el, base) => {
    const layers = []; let n = el;
    while (n?.nodeType === 1) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== "none") {
        if (n === document.body || n === document.documentElement) break;
        return { gradient: true, on: n.tagName + "." + (n.className?.split?.(/\s+/)?.[0] ?? "") };
      }
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 0.999) break; }
      n = n.parentElement;
    }
    let out = n === null || n === document.body || n === document.documentElement ? { ...base } : { r: 255, g: 255, b: 255, a: 1 };
    for (let i = layers.length - 1; i >= 0; i--) out = over(layers[i], out);
    return { color: out };
  };

  /** null when `fg` on `bdColor` clears its required ratio; the failure record otherwise. */
  const contrastFailure = (el, text, cs, fg, bdColor) => {
    const r = ratio(fg, bdColor);
    const px = Number.parseFloat(cs.fontSize);
    const need = px >= 24 || (px >= 18.66 && Number.parseInt(cs.fontWeight, 10) >= 700) ? 3 : 4.5;
    if (r >= need) return null;
    return {
      ratio: Number(r.toFixed(2)), need, text: text.slice(0, 40), color: cs.color,
      disabledControl: el.tagName === "BUTTON" && el.disabled,
      sel: el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\s+/).slice(0, 3).join(".") : ""),
    };
  };

  /** One element's fate, decided without touching `res` -- moving the guard
   *  chain out of the loop body is what keeps `audit` itself flat, since
   *  cognitive complexity charges a nesting bonus per level and this chain
   *  no longer sits inside the `for`. Returns null for "does not count at
   *  all" (a skipped tag, or no text), `{reason}` for a bumped skip,
   *  `{gradient, on, text}` for a gradient backdrop, or `{measured, failure}`
   *  once the element has actually been checked. */
  const classifyElement = (el, base) => {
    if (SKIP.has(el.tagName)) return null;
    const text = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent.trim()).join("").trim();
    if (!text) return null;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return { reason: "hidden" };
    const rect = el.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) return { reason: "zero-size" };
    const op = elementOpacity(el);
    if (op < 0.02) return { reason: "invisible" };
    const fgRaw = parse(cs.color);
    if (!fgRaw) return { reason: "unparsed-color" };
    const bd = backdropColor(el, base);
    if (bd.gradient) return { gradient: true, on: bd.on, text: text.slice(0, 24) };
    const fg = over({ ...fgRaw, a: fgRaw.a * op }, bd.color);
    return { measured: true, failure: contrastFailure(el, text, cs, fg, bd.color) };
  };

  const audit = (base) => {
    const res = { checked: 0, skipped: {}, gradient: [], failures: [] };
    const bump = (k) => (res.skipped[k] = (res.skipped[k] || 0) + 1);
    for (const el of document.querySelectorAll("*")) {
      const result = classifyElement(el, base);
      if (!result) continue;
      if (result.reason) { bump(result.reason); continue; }
      if (result.gradient) { res.gradient.push({ text: result.text, on: result.on }); bump("gradient-backdrop"); continue; }
      res.checked++;
      if (result.failure) res.failures.push(result.failure);
    }
    res.failures.sort((a, b) => a.ratio - b.ratio);
    return res;
  };

  window.__auroraBase = auroraDarkest();
  window.__settle = settle;
  window.__audit = () => audit(window.__auroraBase);
  window.__probe = () => {
    const d = document.createElement("div");
    d.innerHTML =
      '<p style="color:#c9c4be;background:#fff">probe plain</p>' +
      '<p style="color:var(--brand-accent);background:color-mix(in srgb, var(--brand-accent) 16%, transparent)">probe colormix</p>' +
      '<div style="opacity:.35"><p style="color:var(--text-main);background:#fff">probe opacity</p></div>';
    document.body.appendChild(d);
    settle();
    const hits = window.__audit().failures.filter((f) => f.text.startsWith("probe")).map((f) => [f.text, f.ratio]);
    d.remove();
    return { reported: hits, allThreeCaught: hits.length === 3 };
  };
  return { auroraBase: window.__auroraBase, probe: window.__probe() };
})();
