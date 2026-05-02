# Chat Workbench Console Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the main chat workbench so it visually matches the approved dark console reference while preserving current chat, document, prompt, and settings behavior.

**Architecture:** Keep the current `ChatPage` data flow and component boundaries, then reshape the shell through focused JSX cleanup in the chat components plus a consolidated set of chat-page CSS overrides in `pages.css`. Preserve existing handlers, routing, and API usage so this remains a visual refactor rather than a behavior change.

**Tech Stack:** React, TypeScript, React Router, shared global CSS in `frontend/src/styles/pages.css`

---

### Task 1: Refresh the top-level chat shell

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`
- Modify: `frontend/src/styles/pages.css`

- [ ] **Step 1: Keep the current chat wiring intact**

Preserve the existing state hooks, action hooks, polling, drag handlers, session loading, and settings modal flow in `ChatPage.tsx`.

- [ ] **Step 2: Add shell-level wrapper classes only where needed**

Add any minimal wrapper class names needed for the new console layout without moving business logic out of `ChatPage`.

- [ ] **Step 3: Rewrite the page-shell and main region styles**

Rework the main shell CSS so the chat page uses a dark full-height console layout with a fixed-width sidebar, darker content well, and tighter desktop rhythm.

### Task 2: Rebuild the sidebar presentation

**Files:**
- Modify: `frontend/src/pages/chat/components/ChatSidebar.tsx`
- Modify: `frontend/src/pages/chat/components/SessionList.tsx`
- Modify: `frontend/src/pages/chat/components/AgentWorkbench.tsx`
- Modify: `frontend/src/pages/chat/components/PdfWorkbench.tsx`
- Modify: `frontend/src/pages/chat/components/DocumentsPanel.tsx`
- Modify: `frontend/src/pages/chat/components/PromptTemplates.tsx`
- Modify: `frontend/src/pages/chat/components/DocumentItem.tsx`
- Modify: `frontend/src/styles/pages.css`

- [ ] **Step 1: Update sidebar copy hierarchy**

Rename section labels and helper copy toward the approved console language such as `SESSIONS`, `AGENT WORKBENCH`, and `KNOWLEDGE BASE`, while preserving all current actions.

- [ ] **Step 2: Tighten sidebar module markup**

Add small semantic wrappers or badges needed for the new card look, but do not change the props contract between the sidebar and its child components.

- [ ] **Step 3: Restyle session items and tool modules**

Implement the dark navigation rail, active session state, compact module cards, KPI blocks, upload zone, document rows, and prompt rows so the sidebar reads like an operations console instead of a generic admin sidebar.

### Task 3: Refresh the topbar and composer controls

**Files:**
- Modify: `frontend/src/pages/chat/components/ChatTopbar.tsx`
- Modify: `frontend/src/pages/chat/components/ChatComposer.tsx`
- Modify: `frontend/src/styles/pages.css`

- [ ] **Step 1: Simplify the topbar visual language**

Replace the current emoji-heavy header treatment with a tighter control bar that keeps sidebar toggle, settings, theme, architecture, admin, and user menu behavior unchanged.

- [ ] **Step 2: Rework the composer hierarchy**

Adjust the composer markup so the title, textarea, toggles, selects, CTA row, upload action, and quick prompts align with the approved `ASK THE RAG SYSTEM` console panel layout.

- [ ] **Step 3: Restyle controls for the new console system**

Update buttons, toggles, selects, labels, helper text, and dragover state to match the reference dark console treatment while preserving `Ctrl/Cmd + Enter`, `Esc`, and upload behavior.

### Task 4: Refresh messages and supporting cards

**Files:**
- Modify: `frontend/src/pages/chat/components/ChatMessages.tsx`
- Modify: `frontend/src/styles/pages.css`

- [ ] **Step 1: Keep all message rendering behavior intact**

Preserve markdown rendering, metadata chips, execution timeline, citations, graph details, edit, and delete behavior.

- [ ] **Step 2: Update message copy and wrapper classes**

Adjust only the presentation-facing labels and wrappers needed for the new console card system and empty state.

- [ ] **Step 3: Restyle assistant details and empty state**

Rework bubbles, metadata tags, detail panels, citation cards, graph sections, and empty state so they visually align with the approved dark command-center aesthetic.

### Task 5: Validate the refreshed chat workbench

**Files:**
- Test: `frontend/src/pages/ChatPage.tsx`
- Test: `frontend/src/pages/chat/components/ChatSidebar.tsx`
- Test: `frontend/src/pages/chat/components/ChatTopbar.tsx`
- Test: `frontend/src/pages/chat/components/ChatComposer.tsx`
- Test: `frontend/src/pages/chat/components/ChatMessages.tsx`
- Test: `frontend/src/styles/pages.css`

- [ ] **Step 1: Run a frontend build**

Run: `npm run build`

Expected: successful production build with no TypeScript or bundling errors.

- [ ] **Step 2: Smoke-check interaction safety**

Verify that session switching, message sending, stop generation, file upload entry points, prompt actions, settings modal entry, and user menu links still wire through correctly.

- [ ] **Step 3: Review desktop and narrow-width layout**

Confirm the dark console shell remains usable at desktop and narrow widths, especially sidebar open/collapse states, topbar wrapping, and composer control wrapping.
