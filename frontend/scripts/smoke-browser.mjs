/**
 * Does the built application actually come up in a browser?
 *
 * Everything else in CI asks a narrower question. The unit tests render
 * components with jsdom, `npm run build` proves the bundle compiles, and the
 * image jobs prove the containers start -- and all three pass on a deployment
 * that serves a white screen, because none of them loads `index.html` from a
 * server and runs the bundle it names. That is the gap this closes: the classic
 * broken deploy is a hashed asset that 404s, and the only thing that sees it is
 * a browser pointed at the real thing.
 *
 * Deliberately five assertions, each one a distinct failure:
 *
 *   1. `/api/...` returns JSON, not HTML. A reverse proxy that is not reaching
 *      the backend falls through to the SPA and answers every path with
 *      index.html, which looks like a 200 to anything that does not read the
 *      body. This is the assertion the container jobs cannot make: `nginx -t`
 *      parses the configuration, it does not prove a request crosses it.
 *   2. The page itself loads.
 *   3. Nothing threw. An uncaught exception during boot is unambiguous -- it is
 *      not a warning, a deprecation, or a noisy third party.
 *   4. No `/assets/` request 404s. That is the missing-bundle case, scoped to
 *      the hashed files rather than to every request, so a missing favicon
 *      reports without failing a deployment that works.
 *   5. `#root` has children. React mounted; the page is not a blank document
 *      that technically returned 200.
 *
 * Console *errors* are collected and printed but never fail the run: a
 * third-party warning is not a broken deployment, and a check that goes red for
 * one gets switched off.
 *
 *   SMOKE_BASE_URL=http://127.0.0.1:8080 node scripts/smoke-browser.mjs
 */

import { chromium } from "playwright";

const BASE = (process.env.SMOKE_BASE_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "");
// Unauthenticated and served by the backend, so it answers through the proxy
// without a token. A 401 would prove the proxy just as well; a 200 also proves
// the application behind it is answering.
const API_PROBE = "/api/advanced-rag/health";
const TIMEOUT_MS = 30_000;

const failures = [];
const notes = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

// The browser: whatever `npx playwright install chromium` put where Playwright
// expects it, unless SMOKE_CHROMIUM_PATH names one. The override exists because
// a sandbox that ships a Chromium of its own (this repository's agent
// environment does) has it at a path Playwright's version pin does not match,
// and downloading a second copy to run five assertions is not worth the minutes.
const browser = await chromium.launch(
  process.env.SMOKE_CHROMIUM_PATH ? { executablePath: process.env.SMOKE_CHROMIUM_PATH } : {},
);
try {
  const context = await browser.newContext({ baseURL: BASE });
  const page = await context.newPage();

  const pageErrors = [];
  const consoleErrors = [];
  const badAssets = [];

  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.startsWith(BASE) && response.status() >= 400) {
      (url.includes("/assets/") ? badAssets : notes).push(`${response.status()} ${url}`);
    }
  });

  // 1. The API reaches the backend rather than falling through to the SPA.
  // A refused connection throws rather than answering, and an uncaught throw
  // here would report as a crashed script instead of as the failed check it is.
  let api = null;
  let apiType = "";
  try {
    api = await context.request.get(`${BASE}${API_PROBE}`, { timeout: TIMEOUT_MS });
    apiType = api.headers()["content-type"] ?? "";
  } catch (error) {
    failures.push(`${API_PROBE} could not be reached: ${error.message.split("\n")[0]}`);
  }
  check(
    api !== null && apiType.includes("json"),
    `${API_PROBE} answered ${api.status()} ${apiType || "(no content-type)"} -- ` +
      `expected JSON. Anything else means the request did not reach the backend: ` +
      `HTML is the SPA fallback answering, a 5xx is the proxy failing to connect.`,
  );

  // 2-5. The application boots.
  const response = await page.goto(BASE, { waitUntil: "load", timeout: TIMEOUT_MS });
  check(response !== null && response.ok(), `GET ${BASE} answered ${response?.status()}`);

  await page.waitForFunction(() => document.querySelector("#root")?.children.length > 0, null, {
    timeout: TIMEOUT_MS,
  }).catch(() => {});

  const rootChildren = await page.evaluate(() => document.querySelector("#root")?.children.length ?? -1);
  check(rootChildren > 0, `#root has ${rootChildren} children -- the bundle loaded but nothing mounted`);

  const title = await page.title();
  check(title.includes("QueryMind"), `page title is ${JSON.stringify(title)}`);

  check(pageErrors.length === 0, `uncaught page errors: ${pageErrors.join(" | ")}`);
  check(badAssets.length === 0, `assets failed to load: ${badAssets.join(", ")}`);

  console.log(`smoke: ${BASE}`);
  console.log(`  api probe      ${api?.status() ?? "unreachable"} ${apiType}`);
  console.log(`  page           ${response?.status()}, #root children: ${rootChildren}`);
  console.log(`  title          ${title}`);
  console.log(`  page errors    ${pageErrors.length}`);
  console.log(`  console errors ${consoleErrors.length}${consoleErrors.length ? ` (not fatal): ${consoleErrors.join(" | ")}` : ""}`);
  if (notes.length) console.log(`  other 4xx/5xx  ${notes.join(", ")}`);
} finally {
  await browser.close();
}

if (failures.length) {
  console.error("\nFAIL:");
  for (const failure of failures) console.error(`  ${failure}`);
  process.exit(1);
}
console.log("\nthe application serves and boots");
