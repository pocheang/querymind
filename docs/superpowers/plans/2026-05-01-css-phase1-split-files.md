# CSS Phase 1: File Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split large CSS files (>300 lines) into modular, maintainable components under 300 lines each

**Architecture:** Extract logical sections from monolithic CSS files into focused, single-responsibility modules organized by feature/component

**Tech Stack:** Pure CSS, Vite build system, existing project structure

---

## Overview

This plan splits 9 large CSS files (4,894 total lines) into 33 focused modules. Each task extracts a logical section, creates the new file structure, updates imports, and verifies the build.

**Files to split:**
1. dark.css (1257 lines) → 6 files
2. admin.css (769 lines) → 4 files
3. auth.css (698 lines) → 4 files
4. forms.css (410 lines) → 4 files
5. sidebar.css (430 lines) → 3 files
6. composer.css (407 lines) → 3 files
7. buttons.css (364 lines) → 3 files
8. messages.css (283 lines) → 3 files
9. cards.css (276 lines) → 3 files

---

## Task 1: Split dark.css → themes/dark/colors.css

**Files:**
- Read: `frontend/src/styles/themes/dark.css` (lines 1-106)
- Create: `frontend/src/styles/themes/dark/colors.css`
- Modify: `frontend/src/styles/main.css`

- [ ] **Step 1: Create directory structure**

```powershell
New-Item -ItemType Directory -Force -Path "frontend/src/styles/themes/dark"
```

- [ ] **Step 2: Extract color variables (lines 1-106)**

Create `frontend/src/styles/themes/dark/colors.css`:

```css
/* ============================================
   Dark Theme - Color Variables
   Modern Design System - 2026
   ============================================ */

:root[data-theme="dark"] {
  /* Colors - Dark Mode */
  --bg: #08111d;
  --bg-secondary: #0f1b2d;
  --bg-tertiary: #17263a;

  --surface: #101c30;
  --surface-hover: #17253a;
  --surface-active: #22314a;

  --text-primary: #ecf3fb;
  --text-secondary: #c3d0e0;
  --text-tertiary: #8fa0b5;
  --text-inverse: #08111d;

  --border-light: #22324b;
  --border-medium: #334766;
  --border-strong: #506889;

  --accent: #6cb6ff;
  --accent-hover: #91c8ff;
  --accent-light: #12365c;
  --accent-soft: rgba(108, 182, 255, 0.16);

  --success: #44d39c;
  --success-light: #123f34;
  --warning: #f2be5c;
  --warning-light: #4c3412;
  --danger: #ff8b8b;
  --danger-light: #4f1f29;
  --info: #47c7e8;
  --info-light: #143d4e;

  --border: var(--border-light);
  --muted: var(--text-tertiary);
  --text: var(--text-primary);
  --ok: var(--success);
  --panel: rgba(16, 28, 48, 0.96);
  --panel-strong: rgba(11, 20, 34, 0.98);
  --bg-soft: rgba(23, 37, 58, 0.92);

  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.38);
  --shadow-md: 0 8px 20px -12px rgba(0, 0, 0, 0.58), 0 4px 10px -6px rgba(0, 0, 0, 0.36);
  --shadow-lg: 0 16px 30px -16px rgba(0, 0, 0, 0.62), 0 8px 18px -10px rgba(0, 0, 0, 0.4);
  --shadow-xl: 0 28px 52px -24px rgba(0, 0, 0, 0.68), 0 16px 26px -18px rgba(0, 0, 0, 0.44);
  --shadow-2xl: 0 38px 70px -28px rgba(0, 0, 0, 0.74);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #08111d;
    --bg-secondary: #0f1b2d;
    --bg-tertiary: #17263a;

    --surface: #101c30;
    --surface-hover: #17253a;
    --surface-active: #22314a;

    --text-primary: #ecf3fb;
    --text-secondary: #c3d0e0;
    --text-tertiary: #8fa0b5;
    --text-inverse: #08111d;

    --border-light: #22324b;
    --border-medium: #334766;
    --border-strong: #506889;

    --accent: #6cb6ff;
    --accent-hover: #91c8ff;
    --accent-light: #12365c;
    --accent-soft: rgba(108, 182, 255, 0.16);

    --success: #44d39c;
    --success-light: #123f34;
    --warning: #f2be5c;
    --warning-light: #4c3412;
    --danger: #ff8b8b;
    --danger-light: #4f1f29;
    --info: #47c7e8;
    --info-light: #143d4e;

    --border: var(--border-light);
    --muted: var(--text-tertiary);
    --text: var(--text-primary);
    --ok: var(--success);
    --panel: rgba(16, 28, 48, 0.96);
    --panel-strong: rgba(11, 20, 34, 0.98);
    --bg-soft: rgba(23, 37, 58, 0.92);

    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.38);
    --shadow-md: 0 8px 20px -12px rgba(0, 0, 0, 0.58), 0 4px 10px -6px rgba(0, 0, 0, 0.36);
    --shadow-lg: 0 16px 30px -16px rgba(0, 0, 0, 0.62), 0 8px 18px -10px rgba(0, 0, 0, 0.4);
    --shadow-xl: 0 28px 52px -24px rgba(0, 0, 0, 0.68), 0 16px 26px -18px rgba(0, 0, 0, 0.44);
    --shadow-2xl: 0 38px 70px -28px rgba(0, 0, 0, 0.74);
  }
}
```

- [ ] **Step 3: Verify file created**

Run: `Test-Path "frontend/src/styles/themes/dark/colors.css"`
Expected: True

- [ ] **Step 4: Count lines**

Run: `(Get-Content "frontend/src/styles/themes/dark/colors.css").Count`
Expected: ~110 lines (< 300)

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/styles/themes/dark/colors.css
git commit -m "refactor(css): extract dark theme color variables

- Split dark.css colors section into themes/dark/colors.css
- Contains CSS variables and prefers-color-scheme media query
- Part of Phase 1: CSS file splitting (1/33)"
```

---

## Task 2: Split dark.css → themes/dark/auth.css

**Files:**
- Read: `frontend/src/styles/themes/dark.css` (lines 739-898)
- Create: `frontend/src/styles/themes/dark/auth.css`

- [ ] **Step 1: Extract auth page dark styles (lines 739-898)**

Create `frontend/src/styles/themes/dark/auth.css`:

```css
/* ============================================
   Dark Theme - Authentication Pages
   ============================================ */

:root[data-theme="dark"] .auth-root {
  background:
    radial-gradient(circle at top left, rgba(85, 145, 226, 0.18), transparent 34%),
    linear-gradient(180deg, #09131f 0%, #0f1b2d 100%);
}

:root[data-theme="dark"] .theme-toggle {
  border-color: rgba(56, 76, 102, 0.72);
  background: rgba(12, 21, 35, 0.86);
  color: #d3deeb;
}

:root[data-theme="dark"] .theme-toggle:hover {
  border-color: rgba(108, 182, 255, 0.42);
  color: #f4f8fc;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
}

:root[data-theme="dark"] .auth-card {
  background: rgba(12, 22, 36, 0.95);
  border-color: rgba(38, 56, 78, 0.88);
  box-shadow: 0 28px 60px rgba(0, 0, 0, 0.34);
}

:root[data-theme="dark"] .auth-intro {
  background: linear-gradient(180deg, #15314c 0%, #10263c 100%);
}

:root[data-theme="dark"] .auth-intro .badge,
:root[data-theme="dark"] .badge-success {
  background: rgba(9, 18, 31, 0.46);
  border-color: rgba(135, 181, 235, 0.18);
  color: #9fd4ff;
}

:root[data-theme="dark"] .auth-intro h1,
:root[data-theme="dark"] .auth-info-panel h3,
:root[data-theme="dark"] .auth-form h2,
:root[data-theme="dark"] .input-group label {
  color: #eef5fd;
}

:root[data-theme="dark"] .auth-intro p,
:root[data-theme="dark"] .auth-form-subtitle,
:root[data-theme="dark"] .security-tips,
:root[data-theme="dark"] .steps-list,
:root[data-theme="dark"] .help-option p,
:root[data-theme="dark"] .checkline,
:root[data-theme="dark"] .footer-text {
  color: #bfd0e2;
}

:root[data-theme="dark"] .auth-feature-card,
:root[data-theme="dark"] .auth-info-panel,
:root[data-theme="dark"] .help-option {
  background: rgba(14, 24, 39, 0.72);
  border-color: rgba(54, 74, 98, 0.78);
  box-shadow: 0 16px 28px rgba(0, 0, 0, 0.18);
  color: #eef5fd;
}

:root[data-theme="dark"] .auth-feature-icon {
  background: rgba(108, 182, 255, 0.12);
}

:root[data-theme="dark"] .auth-form {
  background: rgba(8, 16, 28, 0.94);
}

:root[data-theme="dark"] .auth-input-shell {
  background: rgba(14, 25, 41, 0.92);
  border-color: rgba(49, 67, 90, 0.92);
}

:root[data-theme="dark"] .auth-input-shell:focus-within {
  border-color: rgba(108, 182, 255, 0.64);
  box-shadow: 0 0 0 4px rgba(108, 182, 255, 0.12);
  background: rgba(17, 31, 51, 0.98);
}

:root[data-theme="dark"] .auth-input-icon {
  color: #8ba0ba;
}

:root[data-theme="dark"] .auth-input-shell input {
  color: #eef5fd;
}

:root[data-theme="dark"] .auth-input-shell input::placeholder {
  color: #8195ae;
}

:root[data-theme="dark"] .hint {
  color: #91a4bc;
}

:root[data-theme="dark"] .hint.ok {
  color: #9ed3ff;
}

:root[data-theme="dark"] .hint.error {
  color: #ff9a9a;
}

:root[data-theme="dark"] .secondary,
:root[data-theme="dark"] button.secondary,
:root[data-theme="dark"] .social-btn,
:root[data-theme="dark"] .link-button {
  background: rgba(16, 29, 47, 0.98);
  border-color: rgba(56, 76, 102, 0.9);
  color: #eef5fd;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.16);
}

:root[data-theme="dark"] .secondary:hover:not(:disabled),
:root[data-theme="dark"] button.secondary:hover:not(:disabled),
:root[data-theme="dark"] .social-btn:hover,
:root[data-theme="dark"] .link-button:hover {
  background: rgba(21, 37, 59, 0.98);
  border-color: rgba(108, 182, 255, 0.48);
  color: #ffffff;
}

:root[data-theme="dark"] .divider::before,
:root[data-theme="dark"] .auth-footer {
  border-color: rgba(49, 67, 90, 0.92);
}

:root[data-theme="dark"] .divider span {
  background: rgba(8, 16, 28, 0.94);
  color: #89a0bb;
}

:root[data-theme="dark"] .auth-footer .text-link,
:root[data-theme="dark"] .text-link-btn {
  color: #8ec8ff;
}

:root[data-theme="dark"] .auth-footer .text-link:hover,
:root[data-theme="dark"] .text-link-btn:hover {
  color: #c9e5ff;
}

:root[data-theme="dark"] .status {
  background: rgba(16, 28, 46, 0.96);
  border-color: rgba(49, 67, 90, 0.92);
  color: #d0dceb;
}

:root[data-theme="dark"] .status.success {
  background: rgba(18, 53, 43, 0.94);
  border-color: rgba(58, 120, 97, 0.82);
  color: #abebd1;
}

:root[data-theme="dark"] .status.error {
  background: rgba(61, 24, 33, 0.94);
  border-color: rgba(123, 56, 69, 0.82);
  color: #ffb8b8;
}
```

- [ ] **Step 2: Verify and count lines**

Run: `(Get-Content "frontend/src/styles/themes/dark/auth.css").Count`
Expected: ~160 lines (< 300)

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/styles/themes/dark/auth.css
git commit -m "refactor(css): extract dark theme auth styles

- Split dark.css auth section into themes/dark/auth.css
- Contains authentication page dark mode overrides
- Part of Phase 1: CSS file splitting (2/33)"
```

---

## Task 3: Update main.css imports for dark theme

**Files:**
- Modify: `frontend/src/styles/main.css:29`

- [ ] **Step 1: Replace dark.css import**

In `frontend/src/styles/main.css`, replace line 29:

```css
@import './themes/dark.css';
```

With:

```css
/* Dark Theme - Modular Structure */
@import './themes/dark/colors.css';
@import './themes/dark/auth.css';
@import './themes/dark/chat.css';
@import './themes/dark/admin.css';
@import './themes/dark/components.css';
@import './themes/dark/effects.css';
```

- [ ] **Step 2: Build and verify**

Run: `cd frontend; npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/styles/main.css
git commit -m "refactor(css): update main.css for modular dark theme

- Replace single dark.css import with 6 modular imports
- Prepares for remaining dark theme file splits
- Part of Phase 1: CSS file splitting (3/33)"
```

---

## Acceptance Criteria

After completing all 33 tasks:

✅ **File Size**
- All CSS files < 300 lines
- Run: `Get-ChildItem frontend/src/styles -Recurse -Filter *.css | ForEach-Object { [PSCustomObject]@{ File = $_.Name; Lines = (Get-Content $_.FullName).Count } } | Where-Object { $_.Lines -gt 300 }`
- Expected: No results

✅ **Build Success**
- Run: `cd frontend; npm run build`
- Expected: Exit code 0, no errors

✅ **Visual Regression**
- Start dev server: `cd frontend; npm run dev`
- Test pages: Login, Chat, Admin, Profile
- Test theme toggle: Light → Dark → Light
- Expected: No visual differences

✅ **Import Structure**
- Verify `main.css` imports all new modular files
- Expected: 33 new files imported correctly

---

## Notes

- Each task is independent and can be executed sequentially
- Always verify build after each commit
- Keep original `dark.css` as backup until all splits complete
- Test theme switching after every 3-4 tasks
- Use `git diff` to verify no CSS rules were lost during extraction


---

## Remaining Tasks (4-33): Simplified Task List

The following tasks follow the same pattern as Tasks 1-3. Each task:
1. Extracts a logical section from the source file
2. Creates a new focused CSS file (< 300 lines)
3. Verifies line count and build success
4. Commits with descriptive message

### Task 4-9: Complete dark.css Split

**Task 4: themes/dark/chat.css**
- Extract: `dark.css` lines 107-450 (chat window, bubbles, messages)
- Target: ~200 lines
- Commit: "refactor(css): extract dark theme chat styles"

**Task 5: themes/dark/admin.css**
- Extract: `dark.css` lines 112-274 (admin panel, tables, forms)
- Target: ~160 lines
- Commit: "refactor(css): extract dark theme admin styles"

**Task 6: themes/dark/components.css**
- Extract: `dark.css` lines 300-700 (buttons, cards, modals, forms)
- Target: ~250 lines
- Commit: "refactor(css): extract dark theme component styles"

**Task 7: themes/dark/effects.css**
- Extract: `dark.css` lines 900-1257 (animations, transitions, scrollbars)
- Target: ~200 lines
- Commit: "refactor(css): extract dark theme effects and animations"

**Task 8: Verify dark.css split complete**
- Verify all 6 files created in `themes/dark/`
- Run build: `cd frontend; npm run build`
- Test theme toggle in browser
- Commit: "refactor(css): complete dark.css modular split"

**Task 9: Remove original dark.css**
- Backup: `mv frontend/src/styles/themes/dark.css frontend/src/styles/themes/dark.css.backup`
- Verify build still works
- Commit: "refactor(css): remove monolithic dark.css file"

---

### Task 10-13: Split admin.css (769 lines → 4 files)

**Task 10: pages/admin/layout.css**
- Extract: `admin.css` lines 1-88 (admin-shell, topbar, panel structure)
- Target: ~90 lines
- Commit: "refactor(css): extract admin layout structure"

**Task 11: pages/admin/dashboard.css**
- Extract: `admin.css` lines 89-195 (KPI cards, section tabs, mini cards)
- Target: ~110 lines
- Commit: "refactor(css): extract admin dashboard components"

**Task 12: pages/admin/forms.css**
- Extract: `admin.css` lines 196-330 (admin forms, inputs, two-col grid)
- Target: ~135 lines
- Commit: "refactor(css): extract admin form styles"

**Task 13: pages/admin/tables.css**
- Extract: `admin.css` lines 331-769 (admin tables, audit table, responsive)
- Target: ~250 lines
- Commit: "refactor(css): extract admin table styles"

**Task 14: Update main.css for admin imports**
- Replace: `@import './pages/admin.css';`
- With: 4 new admin imports
- Verify build
- Commit: "refactor(css): update main.css for modular admin styles"

---

### Task 15-18: Split auth.css (698 lines → 4 files)

**Task 15: pages/auth/layout.css**
- Extract: `auth.css` lines 1-200 (auth-root, auth-card, auth-intro)
- Target: ~200 lines
- Commit: "refactor(css): extract auth page layout"

**Task 16: pages/auth/forms.css**
- Extract: `auth.css` lines 201-400 (auth-form, input-shell, validation)
- Target: ~200 lines
- Commit: "refactor(css): extract auth form components"

**Task 17: pages/auth/social.css**
- Extract: `auth.css` lines 401-537 (social buttons, divider, footer)
- Target: ~140 lines
- Commit: "refactor(css): extract auth social login styles"

**Task 18: pages/auth/dark-mode.css**
- Extract: `auth.css` lines 538-698 (dark theme overrides for auth)
- Target: ~160 lines
- Commit: "refactor(css): extract auth dark mode overrides"

**Task 19: Update main.css for auth imports**
- Replace: `@import './pages/auth.css';`
- With: 4 new auth imports
- Verify build
- Commit: "refactor(css): update main.css for modular auth styles"

---

### Task 20-23: Split forms.css (410 lines → 4 files)

**Task 20: components/forms/inputs.css**
- Extract: `forms.css` lines 1-150 (input, textarea, select base styles)
- Target: ~150 lines
- Commit: "refactor(css): extract form input base styles"

**Task 21: components/forms/groups.css**
- Extract: `forms.css` lines 151-250 (input-group, labels, hints)
- Target: ~100 lines
- Commit: "refactor(css): extract form group styles"

**Task 22: components/forms/auth-inputs.css**
- Extract: `forms.css` lines 251-350 (auth-input-shell, icons)
- Target: ~100 lines
- Commit: "refactor(css): extract auth-specific input styles"

**Task 23: components/forms/validation.css**
- Extract: `forms.css` lines 351-410 (validation, requirements, errors)
- Target: ~60 lines
- Commit: "refactor(css): extract form validation styles"

**Task 24: Update main.css for forms imports**
- Replace: `@import './components/forms.css';`
- With: 4 new forms imports
- Verify build
- Commit: "refactor(css): update main.css for modular form styles"

---

### Task 25-27: Split sidebar.css (430 lines → 3 files)

**Task 25: components/navigation/sidebar-structure.css**
- Extract: `sidebar.css` lines 1-150 (sidebar layout, header, shell)
- Target: ~150 lines
- Commit: "refactor(css): extract sidebar structure"

**Task 26: components/navigation/sidebar-items.css**
- Extract: `sidebar.css` lines 151-300 (menu items, groups, history)
- Target: ~150 lines
- Commit: "refactor(css): extract sidebar menu items"

**Task 27: components/navigation/sidebar-states.css**
- Extract: `sidebar.css` lines 301-430 (collapsed state, hover, active)
- Target: ~130 lines
- Commit: "refactor(css): extract sidebar interaction states"

**Task 28: Update main.css for sidebar imports**
- Replace: `@import './components/sidebar.css';`
- With: 3 new sidebar imports
- Verify build
- Commit: "refactor(css): update main.css for modular sidebar styles"

---

### Task 29-31: Split composer.css (407 lines → 3 files)

**Task 29: features/composer/input-area.css**
- Extract: `composer.css` lines 1-200 (composer-panel, textarea, main)
- Target: ~200 lines
- Commit: "refactor(css): extract composer input area"

**Task 30: features/composer/options.css**
- Extract: `composer.css` lines 201-300 (chat-options-bar, chips, agent select)
- Target: ~100 lines
- Commit: "refactor(css): extract composer options bar"

**Task 31: features/composer/actions.css**
- Extract: `composer.css` lines 301-407 (composer-actions, quick-prompts)
- Target: ~107 lines
- Commit: "refactor(css): extract composer action buttons"

**Task 32: Update main.css for composer imports**
- Replace: `@import './features/composer.css';`
- With: 3 new composer imports
- Verify build
- Commit: "refactor(css): update main.css for modular composer styles"

---

### Task 33: Final Verification & Cleanup

- [ ] **Step 1: Verify all files < 300 lines**

```powershell
Get-ChildItem frontend/src/styles -Recurse -Filter *.css | 
  ForEach-Object { 
    $lines = (Get-Content $_.FullName).Count
    if ($lines -gt 300) {
      Write-Host "$($_.Name): $lines lines (EXCEEDS LIMIT)" -ForegroundColor Red
    }
  }
```

Expected: No output (all files under 300 lines)

- [ ] **Step 2: Full build test**

```powershell
cd frontend
npm run build
```

Expected: Exit code 0, no errors

- [ ] **Step 3: Visual regression test**

```powershell
cd frontend
npm run dev
```

Test checklist:
- [ ] Login page (light theme)
- [ ] Login page (dark theme)
- [ ] Chat page (light theme)
- [ ] Chat page (dark theme)
- [ ] Admin page (light theme)
- [ ] Admin page (dark theme)
- [ ] Theme toggle works smoothly
- [ ] No FOUC (Flash of Unstyled Content)
- [ ] All components render correctly

- [ ] **Step 4: Remove backup files**

```powershell
Remove-Item frontend/src/styles/themes/dark.css.backup -ErrorAction SilentlyContinue
Remove-Item frontend/src/styles/pages/admin.css.backup -ErrorAction SilentlyContinue
Remove-Item frontend/src/styles/pages/auth.css.backup -ErrorAction SilentlyContinue
# ... remove other backups
```

- [ ] **Step 5: Final commit**

```powershell
git add -A
git commit -m "refactor(css): complete Phase 1 file splitting

- Split 9 large CSS files into 33 focused modules
- All files now < 300 lines
- Improved maintainability and code organization
- No visual changes, build verified
- Phase 1 complete: 4,894 lines reorganized"
```

---

## Summary

**Phase 1 Complete:**
- ✅ 9 large files split into 33 focused modules
- ✅ All files < 300 lines (max file reduced from 1257 → ~250 lines)
- ✅ Improved code organization by feature/component
- ✅ Build verified, no visual regressions
- ✅ Git history preserved with descriptive commits

**Next Steps:**
- Phase 2: Critical CSS extraction (14KB inline)
- Phase 3: Route-level code splitting
- Phase 4: Component-level lazy loading

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-05-01-css-phase1-split-files.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
