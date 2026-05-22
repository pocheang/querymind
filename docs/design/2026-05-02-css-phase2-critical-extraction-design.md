# CSS Phase 2: Critical CSS Extraction Design

**Date**: 2026-05-02  
**Type**: Performance Optimization  
**Status**: Design Complete, Ready for Implementation  
**Phase**: 2 of 4 (CSS Optimization Project)

---

## Executive Summary

Extract and inline ~14KB of critical CSS for Login and Chat pages to improve First Contentful Paint (FCP) by 200-400ms. Uses hybrid approach: automated extraction via `critical` package with manual refinement capability, integrated via custom Vite plugin.

**Core Goals:**
- ✅ Inline critical CSS < 14KB in `<head>`
- ✅ Reduce FCP from ~2.5s to ~1.2s (-52%)
- ✅ Eliminate FOUC (Flash of Unstyled Content)
- ✅ Maintain existing route-based code splitting

**Prerequisites:**
- Phase 1 complete: 50 modular CSS files, 99.86 KB bundle
- Vite 6.4.2 build system
- React Router for routing

---

## 1. Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│ Development Flow                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  npm run extract-critical                                   │
│         ↓                                                    │
│  scripts/extract-critical-css.js                            │
│         ↓                                                    │
│  [Start Vite Dev Server]                                    │
│         ↓                                                    │
│  [Analyze /app/ and /app/chat with Puppeteer]              │
│         ↓                                                    │
│  [Extract above-the-fold CSS via critical package]         │
│         ↓                                                    │
│  [Deduplicate + Minify]                                     │
│         ↓                                                    │
│  src/styles/core/critical.css (~14KB)                       │
│         ↓                                                    │
│  [Commit to git]                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Production Build Flow                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  npm run build                                              │
│         ↓                                                    │
│  vite build                                                 │
│         ↓                                                    │
│  vite-plugin-inline-critical.ts                             │
│         ↓                                                    │
│  [Read src/styles/core/critical.css]                        │
│         ↓                                                    │
│  [Inject as <style> in <head>]                             │
│         ↓                                                    │
│  dist/index.html                                            │
│    <head>                                                   │
│      <style data-critical>/* 14KB inlined */</style>       │
│      <link rel="stylesheet" href="main.css">               │
│    </head>                                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

**Extraction Script** (`scripts/extract-critical-css.js`):
- Starts Vite dev server programmatically on port 5173
- Uses `critical` package to analyze rendered pages
- Extracts above-the-fold CSS for desktop (1920x1080) and mobile (375x667)
- Merges results from Login + Chat pages
- Deduplicates selectors and minifies output
- Validates size < 14KB
- Writes to `src/styles/core/critical.css`

**Vite Plugin** (`vite-plugin-inline-critical.ts`):
- Reads `core/critical.css` at build time
- Injects as `<style data-critical>` in `<head>`
- Production builds only (dev mode uses normal imports)
- Fails gracefully if critical.css missing

**Main CSS** (`src/styles/main.css`):
- Imports `core/critical.css` at top of Layer 1
- Ensures critical styles available in dev mode
- Production build inlines it, removes from bundle

**Build Config** (`vite.config.ts`):
- Registers inline-critical plugin
- Maintains existing `cssCodeSplit: true`
- No changes to route-based splitting

### 1.3 Data Flow

**Development Mode:**
```
main.css 
  → @import './core/critical.css'
  → Bundled normally with all other CSS
  → Loaded via <link rel="stylesheet">
```

**Production Mode:**
```
Build Process:
  critical.css → Read by plugin → Inlined in <head>
  main.css → Excludes critical.css → Code-split by route

Browser Load:
  1. HTML arrives with inlined critical CSS (14KB)
  2. First paint happens immediately
  3. Main CSS bundle loads asynchronously
  4. Route-specific CSS loads on navigation
```

---

## 2. Critical CSS Extraction Strategy

### 2.1 Target Pages

**Primary Routes:**
- **Login Page** (`/app/`) - Entry point for all users
- **Chat Page** (`/app/chat`) - Primary application interface

**Rationale:**
- Covers ~90% of first-paint scenarios
- Shared components (buttons, forms) maximize CSS reuse
- Both are high-traffic, performance-critical routes

### 2.2 Viewport Coverage

**Desktop:** 1920x1080 (primary target)
**Mobile:** 375x667 (iPhone SE baseline)

**Why these viewports:**
- Desktop: Most common resolution for web apps
- Mobile: Smallest modern device, ensures mobile-first coverage
- Critical package merges both extractions automatically

### 2.3 Inclusion Rules

**INCLUDE (above-the-fold essentials):**

| Source File | Content | Est. Size |
|-------------|---------|-----------|
| `core/tokens.css` | CSS variables (colors, spacing, typography) | ~2 KB |
| `core/reset.css` | Full CSS reset | ~2 KB |
| `components/buttons/base.css` | Base button styles (no hover/active) | ~1.5 KB |
| `components/forms/inputs.css` | Input field basics | ~1.5 KB |
| `components/sidebar/layout.css` | Sidebar structure (chat page) | ~3 KB |
| `pages/auth/layout.css` | Auth page container (login page) | ~2 KB |
| `themes/light/colors.css` | Light theme color variables | ~2 KB |

**Total Target:** ~14 KB

**EXCLUDE (below-the-fold or interactive):**
- Button hover/active/focus states
- Modal and dropdown styles (not initially visible)
- Dark theme overrides (loaded on theme toggle)
- Animations and transitions (progressive enhancement)
- Admin page styles (separate route)
- Form validation styles (appear on interaction)
- Tooltip and badge styles (conditional rendering)

### 2.4 Extraction Configuration

**Critical Package Options:**
```javascript
{
  base: 'http://localhost:5173',
  src: 'index.html',
  target: {
    html: 'index.html',
    css: 'src/styles/core/critical.css'
  },
  dimensions: [
    { width: 1920, height: 1080 },  // Desktop
    { width: 375, height: 667 }     // Mobile
  ],
  penthouse: {
    timeout: 10000,                  // 10s page load timeout
    renderWaitTime: 500,             // Wait for fonts/images
    blockJSRequests: false           // Allow React to render
  },
  inline: false,                     // We handle inlining via plugin
  minify: true,                      // Minify extracted CSS
  extract: true,                     // Extract to file
  ignore: {
    atrule: ['@font-face'],          // Exclude font-face (loaded separately)
    rule: [/\.modal/, /\.dropdown/]  // Exclude hidden components
  }
}
```

### 2.5 Deduplication Strategy

**Problem:** Critical CSS is extracted AND exists in main bundle → double-loading

**Solution:** PostCSS plugin removes critical selectors from main bundle

**Implementation:**
```javascript
// postcss.config.js
import fs from 'fs';

const criticalCSS = fs.readFileSync('src/styles/core/critical.css', 'utf-8');
const criticalSelectors = extractSelectors(criticalCSS);

export default {
  plugins: [
    {
      postcssPlugin: 'remove-critical-from-bundle',
      Once(root) {
        root.walkRules(rule => {
          if (criticalSelectors.has(rule.selector)) {
            rule.remove();
          }
        });
      }
    }
  ]
};
```

**Result:** Main bundle reduced by ~14KB, no duplicate styles

---

## 3. Implementation Details

### 3.1 Package Dependencies

**New Dependencies:**
```json
{
  "devDependencies": {
    "critical": "^7.2.0",
    "puppeteer": "^23.0.0"
  }
}
```

**Why these packages:**
- `critical`: Industry-standard CSS extraction (Google, Addy Osmani)
- `puppeteer`: Headless Chrome for page rendering (required by critical)

**Bundle Impact:**
- Dev dependencies only, no production bundle impact
- ~2MB added to `node_modules`

### 3.2 Extraction Script

**File:** `scripts/extract-critical-css.js`

**Workflow:**
1. Start Vite dev server programmatically
2. Wait for server ready (poll `http://localhost:5173`)
3. Run `critical.generate()` for `/app/` (Login)
4. Run `critical.generate()` for `/app/chat` (Chat)
5. Merge extracted CSS from both routes
6. Deduplicate selectors (keep first occurrence)
7. Minify using `csso`
8. Validate size < 14KB (fail if exceeded)
9. Write to `src/styles/core/critical.css`
10. Shutdown dev server
11. Exit with code 0 (success) or 1 (failure)

**Error Handling:**
- Server startup timeout: 30s
- Page load timeout: 10s per route
- Size validation: Hard fail if > 14KB
- Empty output: Fail if < 1KB (likely broken)
- Syntax validation: PostCSS parse before writing

**Usage:**
```bash
npm run extract-critical
# or
node scripts/extract-critical-css.js
```

### 3.3 Vite Plugin

**File:** `vite-plugin-inline-critical.ts`

**Hook:** `transformIndexHtml` (runs during HTML generation)

**Logic:**
```typescript
export function inlineCriticalCSS(): Plugin {
  return {
    name: 'vite-plugin-inline-critical',
    apply: 'build', // Production only
    transformIndexHtml(html) {
      const criticalPath = resolve(__dirname, 'src/styles/core/critical.css');
      
      if (!existsSync(criticalPath)) {
        console.warn('⚠️  Critical CSS not found, skipping inline');
        return html;
      }
      
      const criticalCSS = readFileSync(criticalPath, 'utf-8');
      const criticalTag = `<style data-critical>${criticalCSS}</style>`;
      
      // Inject before </head>
      return html.replace('</head>', `${criticalTag}</head>`);
    }
  };
}
```

**Features:**
- Graceful degradation if `critical.css` missing
- Adds `data-critical` attribute for debugging
- Injects before `</head>` (loads before external CSS)
- Production builds only (dev uses normal imports)

### 3.4 Build Configuration

**File:** `vite.config.ts`

**Changes:**
```typescript
import { inlineCriticalCSS } from './vite-plugin-inline-critical';

export default defineConfig({
  plugins: [
    react(),
    inlineCriticalCSS() // Add after react plugin
  ],
  build: {
    cssCodeSplit: true, // Keep existing route-based splitting
    rollupOptions: {
      // Existing config unchanged
    }
  }
});
```

**No changes to:**
- CSS imports in components
- Route-based code splitting
- Existing build optimizations

### 3.5 Main CSS Update

**File:** `src/styles/main.css`

**Change:** Add critical.css import at top of Layer 1

```css
/* LAYER 1: CORE - Foundation */
@import './core/critical.css';  /* ← NEW: Critical CSS for dev mode */
@import './core/tokens.css';
@import './core/reset.css';
@import './core/utilities.css';
```

**Why:**
- Ensures critical styles available in dev mode
- Production build inlines it, removes from bundle
- Maintains single source of truth

---

## 4. Verification & Testing

### 4.1 Build Verification

**Step 1: Extract Critical CSS**
```bash
npm run extract-critical
```

**Expected Output:**
```
✓ Vite dev server started on http://localhost:5173
✓ Analyzing /app/ (Login page)
✓ Analyzing /app/chat (Chat page)
✓ Extracted 13.8 KB critical CSS
✓ Written to src/styles/core/critical.css
✓ Validation passed (< 14KB)
```

**Step 2: Build Production**
```bash
npm run build
```

**Expected Output:**
```
vite v6.4.2 building for production...
✓ 364 modules transformed.
✓ Critical CSS inlined (13.8 KB)
dist/index.html                   0.41 kB → 14.21 kB (critical inlined)
dist/assets/index-[hash].css     99.86 kB → 86.06 kB (critical removed)
dist/assets/index-[hash].js     486.62 kB (unchanged)
✓ built in 3.12s
```

**Step 3: Inspect Output**
```bash
cat dist/index.html | grep -A 5 "data-critical"
```

**Expected:**
```html
<head>
  <style data-critical>
    :root{--bg:#ffffff;--text:#1a1a1a;...}
    /* ~14KB of minified CSS */
  </style>
  <link rel="stylesheet" href="/app/assets/index-abc123.css">
</head>
```

### 4.2 Performance Testing

**Lighthouse CI:**
```bash
npm run lighthouse
```

**Target Metrics:**
- **FCP (First Contentful Paint):** < 1.0s (baseline: 2.5s)
- **LCP (Largest Contentful Paint):** < 2.0s (baseline: 3.5s)
- **TBT (Total Blocking Time):** < 150ms (baseline: 300ms)
- **CLS (Cumulative Layout Shift):** < 0.02 (baseline: 0.05)

**Manual Testing:**
1. Open DevTools → Network tab
2. Throttle to "Fast 3G"
3. Hard reload (Cmd+Shift+R)
4. Observe:
   - First paint happens before CSS file loads ✓
   - No FOUC (flash of unstyled content) ✓
   - Buttons/inputs styled immediately ✓

### 4.3 Visual Regression Testing

**Playwright Test:**
```bash
npm run test:visual
```

**Test Cases:**
- Login page (light theme) - before/after screenshots match
- Login page (dark theme) - before/after screenshots match
- Chat page (light theme) - before/after screenshots match
- Chat page (dark theme) - before/after screenshots match
- Theme toggle - no visual glitches during transition

**Acceptance Criteria:**
- Pixel-perfect match (< 0.1% difference)
- No layout shifts
- No missing styles

### 4.4 Bundle Analysis

**Before Phase 2:**
```
CSS Bundle: 99.86 KB (uncompressed)
Gzipped: 18.12 KB
Critical CSS: 0 KB (none inlined)
```

**After Phase 2:**
```
Critical CSS: 13.8 KB (inlined in HTML)
Main CSS Bundle: 86.06 KB (critical removed)
Gzipped: 15.8 KB (main) + 4.2 KB (critical) = 20.0 KB total
```

**Analysis:**
- Total gzipped size increases slightly (+1.88 KB) due to HTML overhead
- But FCP improves dramatically because critical CSS loads with HTML
- Main bundle reduced by 13.8 KB (critical styles removed)

---

## 5. Error Handling & Rollback

### 5.1 Extraction Script Safeguards

**Server Startup Timeout:**
```javascript
const startServer = async () => {
  const server = await vite.createServer();
  await server.listen();
  
  // Wait for server ready (max 30s)
  const timeout = Date.now() + 30000;
  while (Date.now() < timeout) {
    try {
      await fetch('http://localhost:5173');
      return server;
    } catch {
      await sleep(500);
    }
  }
  throw new Error('Vite server failed to start within 30s');
};
```

**Page Load Timeout:**
```javascript
penthouse: {
  timeout: 10000, // 10s per route
  renderWaitTime: 500
}
```

**Size Validation:**
```javascript
const criticalCSS = fs.readFileSync('src/styles/core/critical.css', 'utf-8');
const sizeKB = Buffer.byteLength(criticalCSS, 'utf-8') / 1024;

if (sizeKB > 14) {
  console.error(`❌ Critical CSS too large: ${sizeKB.toFixed(2)} KB (max 14 KB)`);
  console.error('Breakdown:');
  // Log size by source file
  process.exit(1);
}
```

**Empty Output Check:**
```javascript
if (sizeKB < 1) {
  console.error('❌ Critical CSS suspiciously small (< 1KB), likely extraction failed');
  process.exit(1);
}
```

**Syntax Validation:**
```javascript
import postcss from 'postcss';

try {
  postcss.parse(criticalCSS);
  console.log('✓ CSS syntax valid');
} catch (err) {
  console.error('❌ Invalid CSS syntax:', err.message);
  process.exit(1);
}
```

### 5.2 Build-time Checks

**File Existence:**
```typescript
if (!existsSync(criticalPath)) {
  console.warn('⚠️  Critical CSS not found, skipping inline');
  return html; // Graceful degradation
}
```

**Duplicate Detection:**
```typescript
const mainCSS = readFileSync('dist/assets/index-*.css', 'utf-8');
const duplicates = findDuplicateSelectors(criticalCSS, mainCSS);

if (duplicates.length > 0) {
  console.warn('⚠️  Duplicate selectors found:', duplicates);
  console.warn('Consider updating PostCSS deduplication config');
}
```

**Size Reporting:**
```typescript
console.log(`✓ Critical CSS inlined (${(sizeKB).toFixed(2)} KB)`);
```

### 5.3 Development Experience

**Dev Mode (no inlining):**
- Critical CSS loaded via `@import` in `main.css`
- Normal Vite HMR (Hot Module Replacement)
- No build step required
- Fast iteration

**Production Mode (inlined):**
- Automatic inlining via plugin
- No manual steps
- Reproducible builds (critical.css committed to git)

**Re-extraction Triggers:**
- Major component changes (buttons, forms, layout)
- New above-the-fold content
- Viewport size changes
- Performance regression detected

**When to re-run:**
```bash
# After significant CSS changes
npm run extract-critical
git add src/styles/core/critical.css
git commit -m "chore: update critical CSS extraction"
```

### 5.4 Rollback Strategy

**If critical CSS causes issues:**

**Option 1: Disable plugin (quick rollback)**
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    react(),
    // inlineCriticalCSS() // ← Comment out
  ]
});
```

**Result:** App falls back to normal CSS loading (Phase 1 structure), no code changes needed

**Option 2: Remove critical.css import**
```css
/* main.css */
/* @import './core/critical.css'; */ /* ← Comment out */
@import './core/tokens.css';
```

**Result:** Critical CSS not loaded at all, main bundle unchanged

**Option 3: Full rollback**
```bash
git revert <commit-hash>
npm run build
```

**Result:** Complete rollback to Phase 1 state

### 5.5 Performance Validation

**Lighthouse CI Integration:**
```yaml
# .github/workflows/lighthouse.yml
- name: Run Lighthouse CI
  run: |
    npm run build
    npm run lighthouse -- --assert.assertions.first-contentful-paint=1000
```

**Assertions:**
- FCP < 1000ms (fail build if exceeded)
- LCP < 2000ms
- No FOUC detected (visual regression test)

**Manual Testing Checklist:**
- [ ] Login page loads with styled buttons/inputs immediately
- [ ] Chat page sidebar visible before main CSS loads
- [ ] Theme toggle works (dark theme loads on demand)
- [ ] No layout shifts during page load
- [ ] Mobile viewport (375px) renders correctly

---

## 6. Success Metrics

### 6.1 Technical Metrics

**Bundle Size:**
- ✅ Critical CSS: < 14 KB (inlined)
- ✅ Main CSS: Reduced by ~14 KB (critical removed)
- ✅ Total gzipped: ~20 KB (acceptable overhead)

**Performance:**
- ✅ FCP: < 1.0s (target: 1.2s, baseline: 2.5s)
- ✅ LCP: < 2.0s (target: 2.0s, baseline: 3.5s)
- ✅ TBT: < 150ms (target: 150ms, baseline: 300ms)
- ✅ CLS: < 0.02 (target: 0.02, baseline: 0.05)

**Code Quality:**
- ✅ No duplicate CSS (critical removed from main bundle)
- ✅ Valid CSS syntax (PostCSS validation)
- ✅ Reproducible builds (critical.css committed)

### 6.2 User Experience Metrics

**Visual:**
- ✅ No FOUC (Flash of Unstyled Content)
- ✅ Buttons/inputs styled immediately
- ✅ Layout stable (no shifts)
- ✅ Theme toggle smooth

**Performance:**
- ✅ Perceived load time: -60% (users see content faster)
- ✅ Interaction readiness: Buttons clickable at first paint
- ✅ Mobile experience: Improved on slow networks

### 6.3 Developer Experience Metrics

**Maintainability:**
- ✅ Extraction script: Run manually when needed
- ✅ Build integration: Automatic, no manual steps
- ✅ Rollback: Simple (disable plugin)
- ✅ Debugging: `data-critical` attribute for inspection

**Workflow:**
- ✅ Dev mode: No changes (normal HMR)
- ✅ Production: Automatic inlining
- ✅ CI/CD: Lighthouse assertions prevent regressions

---

## 7. Timeline & Milestones

### 7.1 Implementation Phases

**Phase 2.1: Setup (1-2 hours)**
- Install `critical` and `puppeteer` packages
- Create extraction script skeleton
- Test Vite server programmatic startup

**Phase 2.2: Extraction Script (2-3 hours)**
- Implement `critical.generate()` for Login + Chat
- Add deduplication logic
- Implement size validation
- Test extraction on both routes

**Phase 2.3: Vite Plugin (1-2 hours)**
- Create `vite-plugin-inline-critical.ts`
- Implement `transformIndexHtml` hook
- Add error handling
- Test plugin in production build

**Phase 2.4: Integration (1 hour)**
- Update `vite.config.ts`
- Update `main.css` imports
- Run full build and verify output

**Phase 2.5: Testing & Validation (2-3 hours)**
- Lighthouse CI setup
- Visual regression tests
- Manual testing (dev + prod)
- Performance benchmarking

**Phase 2.6: Documentation (1 hour)**
- Update README with extraction instructions
- Document when to re-run extraction
- Add troubleshooting guide

**Total Estimated Time:** 8-12 hours

### 7.2 Acceptance Criteria

**Before merging to main:**
- [ ] Extraction script runs successfully
- [ ] Critical CSS < 14 KB
- [ ] Production build inlines CSS correctly
- [ ] FCP < 1.2s (Lighthouse)
- [ ] No visual regressions (Playwright)
- [ ] Dev mode works unchanged
- [ ] Documentation updated
- [ ] Code review approved

---

## 8. Future Optimizations

### 8.1 Phase 3 Preview (Route-level Code Splitting)

**Goal:** Split CSS by route, lazy-load on navigation

**Approach:**
- Configure Vite `manualChunks` for route-based CSS splitting
- Preload CSS on link hover
- Maintain critical CSS for initial load

**Expected Impact:**
- First load: 14 KB (critical) + 25 KB (route-specific)
- Navigation: 15-25 KB per route (cached)

### 8.2 Phase 4 Preview (Component-level Lazy Loading)

**Goal:** Lazy-load CSS for modals, dropdowns, tooltips

**Approach:**
- Dynamic imports for low-frequency components
- Suspense boundaries for loading states

**Expected Impact:**
- First load: 14 KB (critical only)
- Modal open: +5 KB (first time only)

### 8.3 Long-term Enhancements

**Automated Re-extraction:**
- Git pre-commit hook to detect CSS changes
- Auto-run extraction if components modified
- Fail commit if critical CSS > 14 KB

**Advanced Optimization:**
- Font subsetting for critical fonts
- SVG icon inlining for above-the-fold icons
- Preconnect to API domains

**Monitoring:**
- Real User Monitoring (RUM) for FCP/LCP
- Alert if metrics regress > 10%
- A/B test critical CSS impact

---

## 9. References

### 9.1 Tools & Packages

- **critical**: https://github.com/addyosmani/critical
- **puppeteer**: https://pptr.dev/
- **Vite Plugin API**: https://vitejs.dev/guide/api-plugin.html
- **Web Vitals**: https://web.dev/vitals/

### 9.2 Best Practices

- **Extract Critical CSS**: https://web.dev/extract-critical-css/
- **Optimize CSS Delivery**: https://web.dev/defer-non-critical-css/
- **Critical Rendering Path**: https://developers.google.com/web/fundamentals/performance/critical-rendering-path

### 9.3 Related Documentation

- **Phase 1 Design**: [2026-05-01-css-optimization-design.md](./2026-05-01-css-optimization-design.md)
- **Phase 1 Plan**: stored in `internal_docs/plans/2026-05-01-css-phase1-split-files.md`
- **Project README**: `README.md`

---

## 10. Appendix

### 10.1 Critical CSS Budget Breakdown

| Category | Files | Est. Size | Priority |
|----------|-------|-----------|----------|
| **Tokens** | `core/tokens.css` | 2 KB | Critical |
| **Reset** | `core/reset.css` | 2 KB | Critical |
| **Buttons** | `components/buttons/base.css` | 1.5 KB | High |
| **Forms** | `components/forms/inputs.css` | 1.5 KB | High |
| **Sidebar** | `components/sidebar/layout.css` | 3 KB | High (chat) |
| **Auth Layout** | `pages/auth/layout.css` | 2 KB | High (login) |
| **Theme** | `themes/light/colors.css` | 2 KB | Critical |
| **Total** | 7 files | **14 KB** | - |

### 10.2 Excluded Styles (Loaded Asynchronously)

| Category | Reason | Load Trigger |
|----------|--------|--------------|
| Button hover states | Not visible until interaction | On hover |
| Modals/Dropdowns | Hidden by default | On open |
| Dark theme | Not default | On theme toggle |
| Animations | Progressive enhancement | After first paint |
| Admin pages | Separate route | On navigation |
| Form validation | Conditional | On submit |

### 10.3 Browser Compatibility

**Supported Browsers:**
- Chrome 90+ ✓
- Firefox 88+ ✓
- Safari 14+ ✓
- Edge 90+ ✓

**Fallback Strategy:**
- Older browsers load full CSS bundle (no inlining)
- Graceful degradation, no broken layouts

---

**Design Document Complete**  
**Next Step:** Create implementation plan via `writing-plans` skill  
**Estimated Implementation Time:** 8-12 hours  
**Expected Performance Gain:** FCP -52%, LCP -43%
