# Auth UI Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the auth pages so they visually match the provided login mockup while preserving existing auth behavior.

**Architecture:** Keep the existing auth page components and shared `auth-*` CSS contract, then reshape markup and shared styles around a unified two-column shell. This limits risk by preserving routes and handlers while centralizing the visual refresh in `components.css`.

**Tech Stack:** React, TypeScript, React Router, shared global CSS in `frontend/src/styles/components.css`

---

### Task 1: Refresh the shared auth visual shell

**Files:**
- Modify: `frontend/src/styles/components.css`

- [ ] **Step 1: Rewrite the auth layout foundation**

Add or replace the auth layout rules so the pages use a centered large white card, soft blue intro panel, shared spacing, and mobile stacking behavior.

- [ ] **Step 2: Add shared component styles**

Add styles for feature cards, icon inputs, helper panels, status blocks, divider rows, and decorative background shapes used by all three auth pages.

- [ ] **Step 3: Add responsive rules**

Ensure the auth card collapses to one column on tablet/mobile, with preserved spacing and button usability.

- [ ] **Step 4: Verify no unrelated selectors are changed**

Re-read the diff and confirm edits stay scoped to auth-related selectors only.

### Task 2: Rebuild the login page markup against the new shell

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Keep existing auth logic and local state**

Preserve validation, remember-me behavior, login/register handlers, and OAuth handlers.

- [ ] **Step 2: Replace the JSX structure**

Update the login page markup so the intro panel, form header, input rows, actions, and social login area align with the reference layout.

- [ ] **Step 3: Add semantic helper wrappers**

Introduce class names for icon fields, feature cards, note text, and action rows that map cleanly to the shared CSS.

- [ ] **Step 4: Verify keyboard and button behavior**

Check that pressing Enter in the password field still triggers login and that disabled states still reflect current validation.

### Task 3: Bring forgot-password into the same design system

**Files:**
- Modify: `frontend/src/pages/ForgotPasswordPage.tsx`

- [ ] **Step 1: Preserve current mock submission flow**

Keep the placeholder async request, success state, and navigation links unchanged in behavior.

- [ ] **Step 2: Rework both visual states**

Refresh both the default and submitted views so they reuse the same auth shell, panel rhythm, and button hierarchy as the login page.

- [ ] **Step 3: Normalize helper content**

Convert the current tips/help blocks into branded info cards and compact support sections that fit the updated layout.

### Task 4: Bring change-password into the same design system

**Files:**
- Modify: `frontend/src/pages/ChangePasswordPage.tsx`

- [ ] **Step 1: Preserve password validation logic**

Keep all existing validation and submit behavior, including the redirect after success.

- [ ] **Step 2: Rework layout and copy hierarchy**

Shift the page into the same dual-column shell, with a security-focused intro panel and a cleaner form section.

- [ ] **Step 3: Restyle password requirements and warnings**

Present requirements as branded checklist cards or rows that visually align with the new auth system.

### Task 5: Validate the refreshed auth pages

**Files:**
- Test: `frontend/src/pages/LoginPage.tsx`
- Test: `frontend/src/pages/ForgotPasswordPage.tsx`
- Test: `frontend/src/pages/ChangePasswordPage.tsx`
- Test: `frontend/src/styles/components.css`

- [ ] **Step 1: Run a frontend build**

Run: `npm run build`

Expected: successful production build with no TypeScript or bundling errors.

- [ ] **Step 2: Smoke-check the affected auth flows**

Manually verify login, register, remember-me, forgot-password submit, forgot-password success state, change-password validation, and change-password submit CTA state.

- [ ] **Step 3: Review responsive layout**

Confirm the refreshed auth shell works at desktop and narrow widths without clipped content or overlapping buttons.
