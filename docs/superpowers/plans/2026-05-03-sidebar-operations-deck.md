# Sidebar Operations Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the chat sidebar into a polished dark operations deck matching the provided reference.

**Architecture:** Keep existing React state, API handlers, and component boundaries. Use small JSX additions for visual structure and implement the visual system in the existing sidebar CSS modules.

**Tech Stack:** React 18, TypeScript, Vite, CSS modules imported through `frontend/src/styles/main.css`.

---

### Task 1: Sidebar Brand And Sessions

**Files:**
- Modify: `frontend/src/pages/chat/components/ChatSidebar.tsx`
- Modify: `frontend/src/pages/chat/components/SessionList.tsx`
- Modify: `frontend/src/styles/components/sidebar/actions.css`
- Modify: `frontend/src/styles/components/sidebar/modern-layout.css`
- Modify: `frontend/src/styles/components/sidebar/modern-sessions.css`

- [ ] **Step 1: Update brand markup**

Add a compact logo mark next to the existing brand text in `ChatSidebar.tsx`. Keep the existing title and subtitle.

- [ ] **Step 2: Update session markup**

In `SessionList.tsx`, convert the current header button into a full-width command row and add a small icon, title, meta text, and count badge for each session row.

- [ ] **Step 3: Style the brand and session deck**

Tune `actions.css`, `modern-layout.css`, and `modern-sessions.css` so the sidebar has the reference-like compact dark glass panel, blue-violet active session state, and tighter command row.

### Task 2: Workbench And Footer Polish

**Files:**
- Modify: `frontend/src/styles/components/sidebar/modules.css`
- Modify: `frontend/src/styles/components/sidebar/footer.css`
- Modify: `frontend/src/styles/components/sidebar/rail.css`
- Modify: `frontend/src/styles/components/sidebar/responsive.css`

- [ ] **Step 1: Align module cards**

Adjust module surfaces to use thin borders, compact radii, darker fills, and subtle hover glow.

- [ ] **Step 2: Align account dock**

Style footer account and action buttons to match the reference dock: compact avatar, quiet icon-like controls, and consistent hover feedback.

- [ ] **Step 3: Preserve responsive behavior**

Keep the mobile sidebar full-height and make sure the session list and tool area still scroll independently.

### Task 3: Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Build frontend**

Run: `npm run build` from `frontend`.
Expected: TypeScript and Vite build complete successfully.

- [ ] **Step 2: Summarize changes**

Report the modified files, build result, and any remaining manual visual checks.
