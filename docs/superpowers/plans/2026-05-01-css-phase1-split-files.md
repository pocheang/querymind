# CSS Phase 1 File Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the 9 large Phase 1 CSS source files into 33 focused modules and update `frontend/src/styles/main.css` so the build output and visual behavior remain unchanged.

**Architecture:** This phase is a file reorganization only. Do not rename selectors, do not introduce CSS Modules, and do not change route-level loading behavior. Extract the new files in source order, switch the `main.css` imports, then remove the legacy monolith files after regression checks pass.

**Tech Stack:** Vite 6, React 18, TypeScript 5, plain CSS, PowerShell, Git

---

## File Structure Map

- `frontend/src/styles/themes/dark/`: `colors.css`, `admin.css`, `components.css`, `auth.css`, `chat.css`, `effects.css`
- `frontend/src/styles/pages/admin/`: `layout.css`, `dashboard.css`, `user-management.css`, `system-settings.css`
- `frontend/src/styles/pages/auth/`: `layout.css`, `login-form.css`, `register-form.css`, `animations.css`
- `frontend/src/styles/components/forms/`: `inputs.css`, `selects.css`, `toggles.css`, `validation.css`
- `frontend/src/styles/components/navigation/`: `sidebar-structure.css`, `sidebar-items.css`, `sidebar-states.css`
- `frontend/src/styles/features/composer/`: `input-area.css`, `quick-prompts.css`, `actions.css`
- `frontend/src/styles/components/buttons/`: `base.css`, `variants.css`, `effects.css`
- `frontend/src/styles/features/messaging/`: `message-bubbles.css`, `message-metadata.css`, `message-actions.css`
- `frontend/src/styles/components/cards/`: `base.css`, `variants.css`, `interactions.css`

## Working Rules

- Before deleting any legacy file, finish creating the replacement files and run `npm run build` from `frontend`.
- Keep every extracted CSS block in original source order to avoid cascade regressions.
- Dark mode sections from `pages/admin.css` and `pages/auth.css` should live only under `themes/dark/`; do not duplicate them in the page split files.
- Commit after every source-file split so each step can be rolled back independently.

### Task 1: Split `dark.css` into `themes/dark/`

**Files:**
- Create: `frontend/src/styles/themes/dark/colors.css` from `frontend/src/styles/themes/dark.css:1-105`
- Create: `frontend/src/styles/themes/dark/admin.css` from `frontend/src/styles/themes/dark.css:108-349`
- Create: `frontend/src/styles/themes/dark/components.css` from `frontend/src/styles/themes/dark.css:350-734`
- Create: `frontend/src/styles/themes/dark/auth.css` from `frontend/src/styles/themes/dark.css:735-907`
- Create: `frontend/src/styles/themes/dark/chat.css` from `frontend/src/styles/themes/dark.css:908-1045`
- Create: `frontend/src/styles/themes/dark/effects.css` from `frontend/src/styles/themes/dark.css:1046-1257`
- Source: `frontend/src/styles/themes/dark.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Preserve the original cascade by extracting contiguous source ranges in order.
- Keep `frontend/src/styles/themes/dark.css` in place until Task 10 switches `main.css` and removes the legacy imports.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/themes/dark' | Out-Null`
Expected: `frontend/src/styles/themes/dark` exists.

- [ ] **Write `frontend/src/styles/themes/dark/colors.css`**

```css
/* ============================================
   Dark Theme - All Dark Mode Styles
   Modern Design System - 2026
   ============================================ */

/* ============================================
   Dark Mode Variables (from base.css)
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

- [ ] **Write `frontend/src/styles/themes/dark/admin.css`**

```css
/* ============================================
   From pages.css
   ============================================ */

:root[data-theme="dark"] .audit-table-wrap {
  background: linear-gradient(180deg, rgba(17, 26, 40, 0.76), rgba(13, 20, 31, 0.86));
}

:root[data-theme="dark"] .admin-shell .panel {
  background: linear-gradient(180deg, rgba(22, 30, 44, 0.92), rgba(16, 24, 36, 0.9));
}

:root[data-theme="dark"] .admin-shell .topbar {
  background:
    linear-gradient(110deg, rgba(19, 85, 163, 0.94), rgba(14, 67, 133, 0.9)),
    radial-gradient(90% 130% at 0% -30%, rgba(255, 255, 255, 0.2), transparent 52%);
}

:root[data-theme="dark"] 

:root[data-theme="dark"] .admin-nav-item.active {
  color: #ecf6ff;
  border-color: rgba(82, 162, 255, 0.5);
  background: linear-gradient(145deg, rgba(40, 136, 227, 0.92), rgba(34, 103, 196, 0.92));
}

:root[data-theme="dark"] 

:root[data-theme="dark"] .admin-mini-card strong {
  color: #9acbff;
}

:root[data-theme="dark"] .admin-shell .ops-two-col input,
:root[data-theme="dark"] .admin-shell .ops-two-col select,
:root[data-theme="dark"] .admin-shell .table td select {
  background: rgba(12, 18, 30, 0.88);
}

:root[data-theme="dark"] .admin-shell .table {
  background: rgba(14, 20, 30, 0.86);
}

:root[data-theme="dark"] .admin-shell .table thead th {
  background: linear-gradient(180deg, rgba(27, 38, 58, 0.9), rgba(22, 32, 49, 0.88));
}

:root[data-theme="dark"] .admin-shell .table tbody tr:hover {
  background: rgba(52, 96, 176, 0.16);
}

:root[data-theme="dark"] .topbar {
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.98));
  border-color: rgba(71, 85, 105, 0.4);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), 0 2px 12px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .topbar::before {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
}

:root[data-theme="dark"] .brand-info h2 {
  background: linear-gradient(135deg, #a5b4fc 0%, #c4b5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

:root[data-theme="dark"] .brand-subtitle {
  color: #94a3b8;
}

:root[data-theme="dark"] .topbar-btn {
  background: rgba(51, 65, 85, 0.8);
  border-color: rgba(71, 85, 105, 0.5);
  color: #e2e8f0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .topbar-btn::before {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
}

:root[data-theme="dark"] .topbar-btn:hover {
  background: rgba(71, 85, 105, 0.9);
  border-color: rgba(102, 126, 234, 0.6);
  color: #f1f5f9;
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.25), 0 2px 8px rgba(0, 0, 0, 0.4);
}

:root[data-theme="dark"] .topbar-btn.admin-btn {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.9), rgba(118, 75, 162, 0.9));
  border-color: rgba(102, 126, 234, 0.7);
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4), 0 2px 6px rgba(102, 126, 234, 0.3);
}

:root[data-theme="dark"] .topbar-btn.admin-btn::before {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.1));
}

:root[data-theme="dark"] .topbar-btn.admin-btn:hover {
  background: linear-gradient(135deg, #667eea, #764ba2);
  box-shadow: 0 8px 28px rgba(102, 126, 234, 0.5), 0 4px 12px rgba(102, 126, 234, 0.4);
}

:root[data-theme="dark"] .brand-logo {
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5), 0 2px 10px rgba(102, 126, 234, 0.35);
}

:root[data-theme="dark"] .brand-logo:hover {
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.6), 0 4px 16px rgba(102, 126, 234, 0.45);
}

:root[data-theme="dark"] .user-badge {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.9), rgba(118, 75, 162, 0.9));
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.4), 0 1px 4px rgba(102, 126, 234, 0.3);
}

:root[data-theme="dark"] .user-badge:hover {
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.5), 0 2px 10px rgba(102, 126, 234, 0.4);
}

:root[data-theme="dark"] .user-menu-dropdown {
  background: rgba(30, 41, 59, 0.98);
  border-color: rgba(71, 85, 105, 0.5);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 4px 16px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(24px) saturate(180%);
}

:root[data-theme="dark"] .user-menu-item {
  color: #e2e8f0;
}

:root[data-theme="dark"] .user-menu-item:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.15));
  color: #c7d2fe;
}

:root[data-theme="dark"] .user-menu-item .menu-icon {
  opacity: 0.8;
}

:root[data-theme="dark"] .user-menu-item:hover .menu-icon {
  opacity: 1;
}

:root[data-theme="dark"] .user-menu-item.logout {
  border-top-color: rgba(71, 85, 105, 0.4);
  color: #fca5a5;
}

:root[data-theme="dark"] .user-menu-item.logout:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.15));
  color: #fecaca;
}

:root[data-theme="dark"] .topbar-divider {
  background: linear-gradient(180deg, transparent, rgba(71, 85, 105, 0.5), transparent);
}

:root[data-theme="dark"] .admin-shell .panel,
:root[data-theme="dark"] .audit-table-wrap {
  background: linear-gradient(180deg, rgba(15, 26, 42, 0.96), rgba(10, 20, 34, 0.94));
  border-color: rgba(46, 66, 92, 0.82);
}

:root[data-theme="dark"] .admin-shell .topbar,
:root[data-theme="dark"] .topbar {
  background:
    linear-gradient(135deg, rgba(15, 29, 48, 0.98), rgba(9, 18, 31, 0.98)),
    radial-gradient(100% 160% at 0% -30%, rgba(102, 182, 255, 0.14), transparent 52%);
  border-color: rgba(57, 78, 105, 0.74);
}

:root[data-theme="dark"] .topbar::before {
  background: linear-gradient(135deg, rgba(102, 182, 255, 0.16), rgba(34, 197, 246, 0.08));
}

:root[data-theme="dark"] .brand-info h2 {
  background: linear-gradient(135deg, #dff1ff 0%, #8ec8ff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

:root[data-theme="dark"] .brand-subtitle,
:root[data-theme="dark"] .sidebar > .muted,
:root[data-theme="dark"] .option-hint,
:root[data-theme="dark"] .process-detail,
:root[data-theme="dark"] .compact-list,
:root[data-theme="dark"] .message-head,
:root[data-theme="dark"] .footer-text {
  color: #9ab0c8;
}

:root[data-theme="dark"] .topbar-btn,
:root[data-theme="dark"] .row-actions .tiny-btn.secondary,
:root[data-theme="dark"] .composer-actions .secondary,
:root[data-theme="dark"] .composer-actions .link-btn {
  background: rgba(20, 35, 56, 0.94);
  border-color: rgba(59, 80, 107, 0.82);
  color: #e9f2fb;
}

:root[data-theme="dark"] .topbar-btn:hover,
:root[data-theme="dark"] .row-actions .tiny-btn.secondary:hover,
:root[data-theme="dark"] .composer-actions .secondary:hover,
:root[data-theme="dark"] .composer-actions .link-btn:hover {
  background: rgba(26, 44, 69, 0.98);
  border-color: rgba(108, 182, 255, 0.48);
  color: #ffffff;
}

:root[data-theme="dark"] .topbar-btn.admin-btn,
:root[data-theme="dark"] .composer-actions .primary-action,
:root[data-theme="dark"] .option-chip.active {
  background: linear-gradient(135deg, #4d93ea 0%, #2f6fc7 100%);
  border-color: rgba(108, 182, 255, 0.72);
  box-shadow: 0 10px 24px rgba(44, 104, 182, 0.34);
}

:root[data-theme="dark"] .user-badge {
  background: linear-gradient(135deg, rgba(71, 146, 237, 0.94), rgba(29, 110, 201, 0.94));
  border-color: rgba(255, 255, 255, 0.16);
}

:root[data-theme="dark"] .user-menu-dropdown {
  background: rgba(12, 23, 39, 0.98);
  border-color: rgba(57, 78, 105, 0.74);
}

:root[data-theme="dark"] .user-menu-item {
  color: #e8f1fb;
}

:root[data-theme="dark"] .user-menu-item:hover {
  background: linear-gradient(135deg, rgba(92, 167, 255, 0.16), rgba(34, 197, 246, 0.08));
  color: #dff1ff;
}
```

- [ ] **Write `frontend/src/styles/themes/dark/components.css`**

```css
:root[data-theme="dark"] .chat-window.panel,
:root[data-theme="dark"] .composer-panel,
:root[data-theme="dark"] .chat-options-bar,
:root[data-theme="dark"] .process-panel,
:root[data-theme="dark"] details,
:root[data-theme="dark"] .citation-card,
:root[data-theme="dark"] .process-step,
:root[data-theme="dark"] .graph-section,
:root[data-theme="dark"] .graph-context,
:root[data-theme="dark"] .profile-card,
:root[data-theme="dark"] .admin-mini-card,
:root[data-theme="dark"] .ops-kpi-card,
:root[data-theme="dark"] .ops-health-card,
:root[data-theme="dark"] .agent-mode-card,
:root[data-theme="dark"] .pdf-kpi-card {
  background: linear-gradient(180deg, rgba(15, 27, 44, 0.94), rgba(10, 19, 33, 0.94));
  border-color: rgba(46, 66, 92, 0.82);
}

:root[data-theme="dark"] .chat-window.panel:hover,
:root[data-theme="dark"] .composer-panel:hover,
:root[data-theme="dark"] .process-panel:hover,
:root[data-theme="dark"] details:hover,
:root[data-theme="dark"] .citation-card:hover,
:root[data-theme="dark"] .process-step:hover,
:root[data-theme="dark"] .agent-mode-card:hover,
:root[data-theme="dark"] .pdf-kpi-card:hover {
  border-color: rgba(108, 182, 255, 0.4);
}

:root[data-theme="dark"] .bubble.assistant {
  background: rgba(18, 31, 50, 0.94);
  border-color: rgba(48, 68, 94, 0.86);
}

:root[data-theme="dark"] .bubble.user {
  background: linear-gradient(135deg, rgba(74, 149, 236, 0.22), rgba(43, 108, 196, 0.2));
  border-color: rgba(108, 182, 255, 0.38);
}

:root[data-theme="dark"] .bubble.assistant .message-role,
:root[data-theme="dark"] .bubble.user .message-role,
:root[data-theme="dark"] .chip,
:root[data-theme="dark"] .process-kind,
:root[data-theme="dark"] details summary:hover,
:root[data-theme="dark"] .quick-prompt-row .tiny-btn,
:root[data-theme="dark"] .brand-logo,
:root[data-theme="dark"] .admin-mini-card strong {
  color: #8ec8ff;
}

:root[data-theme="dark"] .markdown,
:root[data-theme="dark"] .markdown p,
:root[data-theme="dark"] .markdown li,
:root[data-theme="dark"] .markdown h1,
:root[data-theme="dark"] .markdown h2,
:root[data-theme="dark"] .markdown h3,
:root[data-theme="dark"] .section-head strong,
:root[data-theme="dark"] .help-option h4,
:root[data-theme="dark"] .profile-header h1,
:root[data-theme="dark"] .table,
:root[data-theme="dark"] .table thead th,
:root[data-theme="dark"] .table tbody td {
  color: #eaf2fb;
}

:root[data-theme="dark"] .markdown code {
  background: rgba(108, 182, 255, 0.12);
  color: #ffd6d6;
}

:root[data-theme="dark"] .composer-main textarea,
:root[data-theme="dark"] .option-agent select,
:root[data-theme="dark"] .chat-options-bar select,
:root[data-theme="dark"] .admin-shell .ops-two-col input,
:root[data-theme="dark"] .admin-shell .ops-two-col select,
:root[data-theme="dark"] .admin-shell .table td select {
  background: rgba(11, 21, 35, 0.96);
  border-color: rgba(57, 78, 105, 0.74);
  color: #eaf2fb;
}

:root[data-theme="dark"] .composer-main textarea::placeholder,
:root[data-theme="dark"] .option-agent select::placeholder {
  color: #859bb3;
}

:root[data-theme="dark"] .option-hint,
:root[data-theme="dark"] .chip,
:root[data-theme="dark"] .process-kind,
:root[data-theme="dark"] details[open] summary,
:root[data-theme="dark"] .quick-prompt-row .tiny-btn:hover {
  background: rgba(108, 182, 255, 0.1);
  border-color: rgba(108, 182, 255, 0.26);
}

:root[data-theme="dark"] .chat-window.panel {
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.6));
  border-color: rgba(71, 85, 105, 0.4);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4), 0 2px 6px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .chat-window.panel:hover {
  border-color: rgba(102, 126, 234, 0.35);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5), 0 3px 10px rgba(0, 0, 0, 0.35);
}

:root[data-theme="dark"] .bubble.user {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(37, 99, 235, 0.15));
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .bubble.user:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(37, 99, 235, 0.22));
  border-color: rgba(59, 130, 246, 0.55);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2), 0 2px 8px rgba(0, 0, 0, 0.4);
}

:root[data-theme="dark"] .bubble.assistant {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(71, 85, 105, 0.5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .bubble.assistant:hover {
  background: rgba(30, 41, 59, 0.95);
  border-color: rgba(102, 126, 234, 0.45);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15), 0 2px 8px rgba(0, 0, 0, 0.4);
}

:root[data-theme="dark"] .message-head {
  border-bottom-color: rgba(255, 255, 255, 0.1);
}

:root[data-theme="dark"] .row-actions .tiny-btn {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

:root[data-theme="dark"] .row-actions .tiny-btn.secondary {
  background: rgba(51, 65, 85, 0.8);
  border-color: rgba(71, 85, 105, 0.6);
  color: #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .row-actions .tiny-btn.secondary:hover {
  background: rgba(71, 85, 105, 0.95);
  border-color: rgba(102, 126, 234, 0.5);
  color: #f1f5f9;
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(102, 126, 234, 0.25);
}

:root[data-theme="dark"] .row-actions .tiny-btn.danger {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.9), rgba(220, 38, 38, 0.9));
  border-color: rgba(239, 68, 68, 0.6);
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .row-actions .tiny-btn.danger:hover {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border-color: rgba(239, 68, 68, 0.8);
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(239, 68, 68, 0.35);
}

:root[data-theme="dark"] .bubble.user .message-role {
  color: #60a5fa;
}

:root[data-theme="dark"] .bubble.assistant .message-role {
  color: #a78bfa;
}

:root[data-theme="dark"] .markdown code {
  background: rgba(255, 255, 255, 0.1);
  color: #fca5a5;
}

:root[data-theme="dark"] .process-panel,
:root[data-theme="dark"] details {
  background: rgba(30, 41, 59, 0.6);
  border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .process-panel:hover,
:root[data-theme="dark"] details:hover {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(102, 126, 234, 0.3);
}

:root[data-theme="dark"] details summary {
  color: #cbd5e1;
}

:root[data-theme="dark"] details summary:hover {
  color: #a78bfa;
}

:root[data-theme="dark"] details[open] summary {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .process-step {
  background: #1e293b;
  border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .process-step:hover {
  border-color: rgba(102, 126, 234, 0.3);
}

:root[data-theme="dark"] .citation-card {
  background: #1e293b;
  border-color: rgba(255, 255, 255, 0.1);
}

:root[data-theme="dark"] .citation-card:hover {
  border-color: rgba(102, 126, 234, 0.4);
}

:root[data-theme="dark"] .citation-card strong {
  color: #a78bfa;
}

:root[data-theme="dark"] .graph-section {
  background: rgba(30, 41, 59, 0.6);
  border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .graph-context {
  background: #0f172a;
  border-color: rgba(255, 255, 255, 0.1);
}

:root[data-theme="dark"] .empty-chat-label {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  border-color: rgba(102, 126, 234, 0.4);
  color: #a78bfa;
}

:root[data-theme="dark"] .empty-chat-label:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
  border-color: rgba(102, 126, 234, 0.6);
}

:root[data-theme="dark"] .composer-panel {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(71, 85, 105, 0.5);
  box-shadow: 0 8px 28px -8px rgba(0, 0, 0, 0.5), 0 4px 12px -4px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .composer-panel::before {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
}

:root[data-theme="dark"] .composer-panel:hover {
  background: rgba(30, 41, 59, 0.9);
  border-color: rgba(102, 126, 234, 0.4);
  box-shadow: 0 12px 36px -8px rgba(102, 126, 234, 0.2), 0 4px 16px -4px rgba(0, 0, 0, 0.4);
}

:root[data-theme="dark"] .composer-panel:focus-within {
  background: rgba(30, 41, 59, 0.95);
  border-color: rgba(102, 126, 234, 0.6);
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2), 0 12px 36px -8px rgba(102, 126, 234, 0.3);
}

:root[data-theme="dark"] .composer-panel textarea {
  color: #f1f5f9;
}

:root[data-theme="dark"] .composer-panel textarea::placeholder {
  color: #64748b;
}

:root[data-theme="dark"] .composer-label {
  color: #94a3b8;
}

:root[data-theme="dark"] .option-label {
  color: #94a3b8;
}

:root[data-theme="dark"] .chat-options-bar {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
  border-color: rgba(71, 85, 105, 0.4);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .chat-options-bar:hover {
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(51, 65, 85, 0.9) 100%);
  border-color: rgba(102, 126, 234, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

:root[data-theme="dark"] .option-chip {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(71, 85, 105, 0.5);
  color: #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .option-chip:hover {
  background: rgba(30, 41, 59, 0.9);
  border-color: rgba(102, 126, 234, 0.5);
  color: #f1f5f9;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

:root[data-theme="dark"] .option-chip.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: rgba(102, 126, 234, 0.6);
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.4);
}

:root[data-theme="dark"] .option-agent select {
  background: rgba(15, 23, 42, 0.8);
  border-color: rgba(71, 85, 105, 0.5);
  color: #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .option-agent select:hover {
  background: rgba(30, 41, 59, 0.9);
  border-color: rgba(102, 126, 234, 0.5);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

:root[data-theme="dark"] .option-agent select:focus {
  border-color: rgba(102, 126, 234, 0.6);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

:root[data-theme="dark"] .option-hint {
  background: rgba(15, 23, 42, 0.6);
  border-color: rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
}

:root[data-theme="dark"] .composer-actions button.secondary,
:root[data-theme="dark"] .composer-actions .link-btn {
  background: #0f172a;
  border-color: rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
}

:root[data-theme="dark"] .composer-actions button.secondary:hover,
:root[data-theme="dark"] .composer-actions .link-btn:hover {
  background: #1e293b;
  border-color: rgba(102, 126, 234, 0.4);
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn {
  background: #0f172a;
  border-color: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn:hover {
  background: #1e293b;
  border-color: rgba(102, 126, 234, 0.4);
  color: #a78bfa;
}

:root[data-theme="dark"] .composer-panel.dragover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
  border-color: rgba(102, 126, 234, 0.5);
}

:root[data-theme="dark"] .status {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.15));
  border-color: rgba(16, 185, 129, 0.3);
  color: #34d399;
}

:root[data-theme="dark"] .status.error {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.15));
  border-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}
```

- [ ] **Write `frontend/src/styles/themes/dark/auth.css`**

```css
/* ============================================
   From components.css
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

:root[data-theme="dark"] .citation-card {
  background: rgba(17, 26, 40, 0.7);
}

:root[data-theme="dark"] .process-step {
  background: linear-gradient(180deg, rgba(23, 33, 50, 0.9), rgba(16, 25, 40, 0.88));
}
```

- [ ] **Write `frontend/src/styles/themes/dark/chat.css`**

```css
/* ============================================
   From chat-workbench.css
   ============================================ */

:root[data-theme="dark"] {
  --work-bg: #09131f;
  --work-surface: #0f1d31;
  --work-surface-soft: #16253a;
  --work-rail: #08111b;
  --work-rail-2: #0f1927;
  --work-text: #eaf2fb;
  --work-muted: #95a6bb;
  --work-line: #22344d;
  --work-line-strong: #3a5070;
  --work-blue: #67b2ff;
  --work-blue-soft: #102d4b;
  --work-green: #46d49e;
  --work-amber: #e0a640;
  --work-red: #ef7a88;
  --work-shadow: 0 24px 60px -34px rgba(0, 0, 0, 0.7);
}

:root[data-theme="dark"] .ops-kpi-card {
  background: rgba(17, 26, 40, 0.76);
}

:root[data-theme="dark"] .ops-auto-refresh {
  background: rgba(12, 18, 30, 0.88);
}

:root[data-theme="dark"] .ops-trend-list {
  background: rgba(17, 26, 40, 0.76);
}

:root[data-theme="dark"] .diagram-block {
  background: rgba(17, 26, 40, 0.7);
}

:root[data-theme="dark"] .agent-mode-card {
  background: linear-gradient(160deg, rgba(17, 26, 40, 0.9), rgba(15, 22, 34, 0.86));
}

:root[data-theme="dark"] .pdf-kpi-card {
  background: rgba(17, 26, 40, 0.74);
}

/* ============================================
   From modern-ui-enhancements.css
   ============================================ */

:root[data-theme="dark"] .bubble.assistant {
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(30, 41, 59, 0.6);
}

:root[data-theme="dark"] .bubble.user {
  border-color: rgba(102, 126, 234, 0.3);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
}

:root[data-theme="dark"] details {
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(15, 23, 42, 0.4);
}

:root[data-theme="dark"] details summary {
  background: rgba(30, 41, 59, 0.5);
  border-bottom-color: rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
}

:root[data-theme="dark"] details[open] summary {
  background: rgba(102, 126, 234, 0.15);
  color: #a5b4fc;
}

:root[data-theme="dark"] .compact-list {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.6), rgba(30, 41, 59, 0.6));
  color: #94a3b8;
}

:root[data-theme="dark"] .process-step {
  border-color: rgba(255, 255, 255, 0.08);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(51, 65, 85, 0.6));
}

:root[data-theme="dark"] .citation-card {
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(30, 41, 59, 0.5);
}

:root[data-theme="dark"] .composer-panel {
  border-color: rgba(255, 255, 255, 0.08);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.8));
}

:root[data-theme="dark"] .composer-main textarea {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(15, 23, 42, 0.6);
  color: #f1f5f9;
}

:root[data-theme="dark"] .chat-options-bar {
  background: rgba(15, 23, 42, 0.5);
  border-color: rgba(255, 255, 255, 0.06);
}

:root[data-theme="dark"] .option-chip {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(30, 41, 59, 0.6);
  color: #cbd5e1;
}

:root[data-theme="dark"] .option-chip:hover {
  border-color: rgba(102, 126, 234, 0.4);
  background: rgba(102, 126, 234, 0.15);
}

:root[data-theme="dark"] .option-agent select,
:root[data-theme="dark"] .chat-options-bar select {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(15, 23, 42, 0.6);
  color: #e2e8f0;
}

:root[data-theme="dark"] .composer-actions .secondary,
:root[data-theme="dark"] .composer-actions .link-btn {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(30, 41, 59, 0.6);
  color: #cbd5e1;
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn {
  border-color: rgba(102, 126, 234, 0.3);
  background: rgba(102, 126, 234, 0.1);
  color: #a5b4fc;
}
```

- [ ] **Write `frontend/src/styles/themes/dark/effects.css`**

```css
/* ============================================
   From final-polish.css
   ============================================ */

:root[data-theme="dark"] .composer-panel {
  border-color: rgba(255, 255, 255, 0.12);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.9));
}

:root[data-theme="dark"] .composer-label {
  color: #cbd5e1;
}

:root[data-theme="dark"] .composer-main textarea {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(15, 23, 42, 0.8);
  color: #f1f5f9;
}

:root[data-theme="dark"] .chat-options-bar {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.7), rgba(30, 41, 59, 0.7));
  border-color: rgba(255, 255, 255, 0.1);
}

:root[data-theme="dark"] .option-label {
  color: #cbd5e1;
}

:root[data-theme="dark"] .option-chip {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.8);
  color: #cbd5e1;
}

:root[data-theme="dark"] .option-agent select,
:root[data-theme="dark"] .chat-options-bar select {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(15, 23, 42, 0.8);
  color: #e2e8f0;
}

:root[data-theme="dark"] .option-hint {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  border-color: rgba(102, 126, 234, 0.25);
  color: #cbd5e1;
}

:root[data-theme="dark"] .composer-actions .secondary,
:root[data-theme="dark"] .composer-actions .link-btn {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.8);
  color: #cbd5e1;
}

:root[data-theme="dark"] .bubble.assistant {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(30, 41, 59, 0.7);
}

:root[data-theme="dark"] .bubble.user {
  border-color: rgba(102, 126, 234, 0.35);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.18), rgba(118, 75, 162, 0.18));
}

/* ============================================
   From ui-polish.css
   ============================================ */

:root[data-theme="dark"] .composer-main textarea {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(15, 23, 42, 0.7);
  color: #f1f5f9;
}

:root[data-theme="dark"] .composer-main textarea::placeholder {
  color: #64748b;
}

:root[data-theme="dark"] .chat-options-bar {
  background: rgba(15, 23, 42, 0.6);
  border-color: rgba(255, 255, 255, 0.08);
}

:root[data-theme="dark"] .option-label {
  color: #94a3b8;
}

:root[data-theme="dark"] .option-chip {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(30, 41, 59, 0.7);
  color: #cbd5e1;
}

:root[data-theme="dark"] .option-agent select,
:root[data-theme="dark"] .chat-options-bar select {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(15, 23, 42, 0.7);
  color: #e2e8f0;
}

:root[data-theme="dark"] .option-hint {
  background: rgba(102, 126, 234, 0.12);
  border-color: rgba(102, 126, 234, 0.2);
  color: #cbd5e1;
}

:root[data-theme="dark"] .markdown {
  color: #e2e8f0;
}

:root[data-theme="dark"] .markdown h1,
:root[data-theme="dark"] .markdown h2,
:root[data-theme="dark"] .markdown h3 {
  color: #f1f5f9;
}

:root[data-theme="dark"] .markdown code {
  background: rgba(102, 126, 234, 0.15);
  color: #a5b4fc;
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn {
  border-color: rgba(102, 126, 234, 0.25);
  background: rgba(102, 126, 234, 0.08);
  color: #a5b4fc;
  opacity: 0.9;
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn:hover {
  opacity: 1;
  border-color: rgba(102, 126, 234, 0.4);
  background: rgba(102, 126, 234, 0.15);
}

:root[data-theme="dark"] * {
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

:root[data-theme="dark"] *::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}

:root[data-theme="dark"] *::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}

/* ============================================
   From precision-adjustments.css
   ============================================ */

:root[data-theme="dark"] .option-chip {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .option-chip::before {
  background: #e2e8f0;
}

:root[data-theme="dark"] .option-chip:hover {
  background: rgba(255, 255, 255, 0.15);
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn {
  border-color: rgba(102, 126, 234, 0.3);
  color: #a5b4fc;
}

:root[data-theme="dark"] .quick-prompt-row .tiny-btn:hover {
  border-color: rgba(102, 126, 234, 0.5);
  background: rgba(102, 126, 234, 0.12);
  color: #c7d2fe;
}

:root[data-theme="dark"] .composer-main textarea {
  border-color: rgba(255, 255, 255, 0.15);
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.9));
  color: #f1f5f9;
}

:root[data-theme="dark"] .composer-main textarea::placeholder {
  color: #64748b;
}

:root[data-theme="dark"] .composer-main textarea:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(51, 65, 85, 0.95));
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .composer-main textarea:focus {
  border-color: rgba(102, 126, 234, 0.8);
  background: rgba(15, 23, 42, 1);
  box-shadow:
    0 0 0 4px rgba(102, 126, 234, 0.2),
    0 0 0 8px rgba(102, 126, 234, 0.1),
    0 4px 12px rgba(102, 126, 234, 0.25),
    inset 0 1px 2px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .chat-options-bar {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.8));
  border-color: rgba(255, 255, 255, 0.1);
}

:root[data-theme="dark"] .option-label {
  color: #cbd5e1;
}

:root[data-theme="dark"] .quick-prompt-row::after {
  background: linear-gradient(90deg, transparent, rgba(30, 41, 59, 0.9));
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify dark theme rendering on `/login`, `/chat`, and `/admin`.

- [ ] **Commit**

```bash
git add frontend/src/styles/themes/dark/colors.css frontend/src/styles/themes/dark/admin.css frontend/src/styles/themes/dark/components.css frontend/src/styles/themes/dark/auth.css frontend/src/styles/themes/dark/chat.css frontend/src/styles/themes/dark/effects.css
git commit -m "refactor(css): split dark theme styles into theme modules"
```

### Task 2: Split `admin.css` into `pages/admin/`

**Files:**
- Create: `frontend/src/styles/pages/admin/layout.css` from `frontend/src/styles/pages/admin.css:1-137`
- Create: `frontend/src/styles/pages/admin/dashboard.css` from `frontend/src/styles/pages/admin.css:138-379`
- Create: `frontend/src/styles/pages/admin/user-management.css` from `frontend/src/styles/pages/admin.css:380-463`
- Create: `frontend/src/styles/pages/admin/system-settings.css` from `frontend/src/styles/pages/admin.css:464-769`
- Source: `frontend/src/styles/pages/admin.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Do not duplicate the `admin.css` dark mode block inside `pages/admin/`; Task 1 moves that responsibility to `themes/dark/admin.css`.
- Keep the audit/settings-related sections together in `system-settings.css` so the split still lands at four files.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/pages/admin' | Out-Null`
Expected: `frontend/src/styles/pages/admin` exists.

- [ ] **Write `frontend/src/styles/pages/admin/layout.css`**

```css
/* ============================================
   Admin Page
   ============================================ */

.admin-shell {
  min-height: 100vh;
  background: var(--bg);
  padding: var(--space-8);
  max-width: 1440px;
  margin: 0 auto;
}

.admin-shell .topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-6) var(--space-8);
  background: linear-gradient(135deg, var(--accent) 0%, var(--info) 100%);
  border: 1px solid var(--accent);
  border-radius: var(--radius-2xl);
  color: var(--text-inverse);
  box-shadow: var(--shadow-xl);
  margin-bottom: var(--space-8);
  gap: var(--space-4);
}

.admin-shell .topbar h2 {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin: 0;
  color: var(--text-inverse);
}

.admin-shell .topbar .muted {
  color: rgba(255, 255, 255, 0.9);
  font-size: var(--text-base);
}

.admin-shell .topbar .top-actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.admin-shell .topbar button {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: var(--text-inverse);
  backdrop-filter: blur(10px);
}

.admin-shell .topbar button:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}

.admin-shell .panel {
  margin-top: 0;
  border-radius: 20px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--accent) 8%, var(--border));
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.9));
  box-shadow:
    0 18px 36px -30px rgba(16, 42, 82, 0.36),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.admin-shell .section-head {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed color-mix(in srgb, var(--accent) 18%, var(--border));
}

.admin-shell .section-head strong {
  font-size: 18px;
  letter-spacing: 0.05px;
  font-weight: 800;
}

.admin-nav-item.active {
  color: #fff;
  border-color: #1b7fd4;
  background: linear-gradient(145deg, #23a5ff, #1e75d8);
  box-shadow: 0 12px 20px -14px rgba(18, 93, 175, 0.8);
}

/* ============================================
   Admin Section Tabs
   ============================================ */

.admin-section-tabs {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding: var(--space-3);
  background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 4%, var(--surface)), var(--surface));
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
}

.admin-section-tabs button {
  padding: var(--space-3) var(--space-5);
  font-size: var(--text-sm);
  font-weight: 600;
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
  min-height: 40px;
}

.admin-section-tabs button:not(.secondary) {
  background: var(--accent);
  color: var(--text-inverse);
  box-shadow: var(--shadow-sm);
}

.admin-section-tabs button.secondary {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid transparent;
}

.admin-section-tabs button.secondary:hover {
  background: var(--surface-hover);
  border-color: var(--border-medium);
}

.admin-shell .admin-section-tabs {
  gap: 10px;
}

.admin-shell .admin-section-tabs button {
  min-width: 120px;
  border-radius: 999px;
}
```

- [ ] **Write `frontend/src/styles/pages/admin/dashboard.css`**

```css
/* ============================================
   Admin KPI Cards
   ============================================ */

.admin-kpi-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
}

.admin-kpi-card span {
  font-size: 12px;
  opacity: 0.92;
}

.admin-kpi-card strong {
  font-size: 26px;
  line-height: 1.05;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.ops-kpi-card,
.ops-kpi-card:hover,
.admin-kpi-card:hover {
  border-color: var(--accent);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
  transform: translateY(-3px);
}

.ops-kpi-card span,
.admin-kpi-card span {
  display: block;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
  font-weight: 500;
}

.ops-kpi-card strong,
.admin-kpi-card strong {
  display: block;
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--text-primary);
}

.admin-shell .ops-kpi-card,
.admin-shell .ops-health-card,
.admin-shell .ops-trend-list {
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--accent) 10%, var(--border));
}

.admin-shell .ops-kpi-card strong {
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

/* ============================================
   Admin Forms & Inputs
   ============================================ */

.ops-two-col,
.admin-filter-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.admin-field {
  display: grid;
  gap: 7px;
}

.admin-field span {
  font-size: 12px;
  font-weight: 700;
  color: color-mix(in srgb, var(--text) 72%, var(--muted));
  letter-spacing: 0.2px;
}

.admin-field input {
  margin-top: 0;
  height: 46px;
  border-radius: 12px;
}

.admin-field input,
.admin-field select,
.admin-field textarea {
  width: 100%;
  border: 1.5px solid var(--border-light);
  border-radius: 10px;
  transition: all 0.2s ease;
}

.admin-field input:hover,
.admin-field select:hover,
.admin-field textarea:hover {
  border-color: var(--border-medium);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.admin-field input:focus,
.admin-field select:focus,
.admin-field textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.admin-shell .ops-two-col input,
.admin-shell .ops-two-col select {
  margin-top: 0;
  height: 44px;
  border-radius: 12px;
  border: 1.5px solid color-mix(in srgb, var(--accent) 8%, var(--border));
  background: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
  transition: all 0.2s ease;
}

.admin-shell .ops-two-col input:hover,
.admin-shell .ops-two-col select:hover {
  border-color: color-mix(in srgb, var(--accent) 25%, var(--border));
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.admin-shell .ops-two-col input:focus,
.admin-shell .ops-two-col select:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--accent) 55%, #9abdf2);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.row-actions.wrap {
  margin-top: 8px;
}

.admin-shell .row-actions button,
.admin-shell .row-actions .link-btn {
  min-height: 38px;
  transition: transform 0.16s ease, box-shadow 0.18s ease, filter 0.16s ease;
}

.admin-shell .row-actions button:hover,
.admin-shell .row-actions .link-btn:hover {
  transform: translateY(-1.5px);
  filter: brightness(1.04);
  box-shadow: 0 14px 24px -18px rgba(27, 77, 144, 0.55);
}

.admin-shell .admin-field input,
.admin-shell .admin-field select,
.admin-shell .admin-field textarea {
  min-height: 44px;
  border-radius: 14px;
}

.admin-shell .admin-field textarea {
  min-height: 112px;
}

.admin-shell .muted {
  font-size: 13px;
}

.admin-shell .status {
  margin-top: 0;
  border: 1px solid color-mix(in srgb, var(--ok) 38%, var(--border));
  background: color-mix(in srgb, var(--ok) 12%, transparent);
  border-radius: 12px;
  padding: 8px 10px;
}

.admin-shell .status.error {
  border-color: color-mix(in srgb, var(--danger) 42%, var(--border));
  background: color-mix(in srgb, var(--danger) 12%, transparent);
}

.admin-shell .tiny-btn {
  border-radius: 10px;
}

/* ============================================
   Admin Tables
   ============================================ */

.admin-shell .table {
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--accent) 9%, var(--border));
  background: #fff;
  box-shadow: 0 14px 32px -28px rgba(15, 23, 42, 0.35);
}

.admin-shell .table thead th {
  font-size: 11px;
  font-weight: 700;
  color: color-mix(in srgb, var(--text) 72%, var(--muted));
  text-transform: uppercase;
  letter-spacing: 0.45px;
  background: linear-gradient(180deg, #f7faff, #f3f7ff);
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 10%, var(--border));
}

.admin-shell .table tbody tr {
  transition: background-color 0.14s ease;
}

.admin-shell .table tbody tr:hover {
  background: #f6faff;
}

.admin-shell .table td,
.admin-shell .table th {
  padding: 11px 10px;
}

.admin-shell .table td .row-actions {
  gap: 8px;
}

.admin-shell .table td select {
  margin-top: 0;
  height: 34px;
  border-radius: 10px;
  padding: 0 10px;
  background: #fff;
}
```

- [ ] **Write `frontend/src/styles/pages/admin/user-management.css`**

```css
/* ============================================
   Admin Create Panel
   ============================================ */

.admin-create-panel {
  display: grid;
  gap: 12px;
}

.admin-create-hint {
  margin-top: -4px;
  font-size: 13px;
}

.admin-create-grid {
  gap: 14px;
}

.admin-create-actions {
  display: grid;
  align-items: end;
}

.admin-create-actions button {
  width: 100%;
  height: 46px;
  border-radius: 12px;
  font-size: 14px;
  letter-spacing: 0.2px;
}

/* ============================================
   Admin Users Panel
   ============================================ */

.admin-users-panel {
  display: grid;
  gap: 12px;
}

.admin-users-hint {
  margin-top: -4px;
  font-size: 13px;
}

.admin-filter-grid {
  gap: 14px;
}

.admin-user-table {
  table-layout: fixed;
}

.admin-user-table th,
.admin-user-table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-user-table th:first-child,
.admin-user-table td:first-child {
  width: 286px;
}

.admin-user-id {
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 12px;
}

.admin-username {
  font-weight: 700;
}

.user-row-actions {
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: nowrap;
}

.user-row-actions .tiny-btn {
  min-width: 68px;
}
```

- [ ] **Write `frontend/src/styles/pages/admin/system-settings.css`**

```css
/* ============================================
   Admin Audit Panel
   ============================================ */

.admin-audit-panel {
  display: grid;
  gap: 12px;
}

.admin-audit-hint {
  margin-top: -4px;
  font-size: 13px;
}

.admin-audit-head-actions select {
  min-width: 168px;
  height: 36px;
  margin-top: 0;
}

.admin-audit-quick-actions {
  align-self: end;
  justify-content: flex-start;
}

.audit-table-wrap {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--accent) 10%, var(--border));
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(249, 252, 255, 0.9));
}

.admin-audit-table {
  min-width: 1760px;
  width: 100%;
  table-layout: fixed;
  border: 0;
  background: transparent;
}

.admin-audit-table th,
.admin-audit-table td {
  vertical-align: top;
  white-space: nowrap;
  overflow-wrap: normal;
  word-break: normal;
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 8%, var(--border));
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-audit-table th {
  white-space: nowrap;
  overflow-wrap: normal;
  word-break: keep-all;
}

.admin-audit-table th:nth-child(1),
.admin-audit-table td:nth-child(1) {
  min-width: 170px;
}

.admin-audit-table th:nth-child(2),
.admin-audit-table td:nth-child(2) {
  min-width: 260px;
}

.admin-audit-table th:nth-child(3),
.admin-audit-table td:nth-child(3) {
  min-width: 220px;
}

.admin-audit-table th:nth-child(6),
.admin-audit-table td:nth-child(6) {
  min-width: 260px;
}

.admin-audit-table th:nth-child(9),
.admin-audit-table td:nth-child(9) {
  min-width: 360px;
}

.admin-audit-table th:nth-child(10),
.admin-audit-table td:nth-child(10) {
  min-width: 300px;
}

.admin-audit-table th:nth-child(8),
.admin-audit-table td:nth-child(8) {
  min-width: 110px;
}

.audit-time {
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 12px;
}

.admin-audit-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
}

.admin-audit-table tbody tr:nth-child(2n) {
  background: rgba(42, 122, 220, 0.03);
}

.admin-audit-table tbody tr:hover {
  background: rgba(42, 122, 220, 0.08);
}

.audit-cell-stack {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.audit-sub {
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.audit-id {
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.audit-code {
  display: inline-block;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent) 14%, var(--border));
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 12px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: top;
}

.audit-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 58px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent) 14%, var(--border));
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  font-size: 12px;
  font-weight: 700;
  text-transform: lowercase;
}

.audit-user-agent,
.audit-detail {
  white-space: nowrap;
  line-height: 1.35;
  font-size: 12px;
  color: color-mix(in srgb, var(--text) 88%, var(--muted));
  overflow: hidden;
  text-overflow: ellipsis;
}

.audit-actor,
.audit-action,
.audit-resource {
  white-space: nowrap;
  line-height: 1.45;
}

.admin-audit-scroll-hint {
  margin-top: -2px;
  margin-bottom: 2px;
  font-size: 12px;
}

.audit-ip {
  white-space: nowrap;
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
}

.admin-audit-match-hint {
  margin-top: -6px;
}

/* ============================================
   Responsive
   ============================================ */

@media (max-width: 860px) {
  .admin-shell {
    padding: 12px 10px;
    gap: 10px;
  }

  .admin-shell .panel {
    padding: 10px;
    border-radius: 14px;
  }

  .admin-shell .topbar {
    border-radius: 14px;
    padding: 12px;
    align-items: flex-start;
  }

  .admin-shell .topbar .top-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .admin-shell .table {
    border-radius: 10px;
    font-size: 12px;
  }

  .admin-shell .table td,
  .admin-shell .table th {
    padding: 8px 7px;
  }

  .user-row-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .admin-user-table th:first-child,
  .admin-user-table td:first-child {
    width: 210px;
  }

  .admin-audit-head-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .admin-audit-head-actions select {
    min-width: 140px;
  }

  .admin-audit-quick-actions {
    align-self: start;
  }

  .admin-shell .admin-section-tabs button {
    flex: 1 1 140px;
  }
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify `/admin` topbar, KPI cards, user table, audit table, and responsive layout.

- [ ] **Commit**

```bash
git add frontend/src/styles/pages/admin/layout.css frontend/src/styles/pages/admin/dashboard.css frontend/src/styles/pages/admin/user-management.css frontend/src/styles/pages/admin/system-settings.css
git commit -m "refactor(css): split admin page stylesheet by responsibility"
```

### Task 3: Split `auth.css` into `pages/auth/`

**Files:**
- Create: `frontend/src/styles/pages/auth/layout.css` from `frontend/src/styles/pages/auth.css:1-49,61-227`
- Create: `frontend/src/styles/pages/auth/login-form.css` from `frontend/src/styles/pages/auth.css:228-452`
- Create: `frontend/src/styles/pages/auth/register-form.css` from `frontend/src/styles/pages/auth.css:453-534`
- Create: `frontend/src/styles/pages/auth/animations.css` from `frontend/src/styles/pages/auth.css:50-59`
- Source: `frontend/src/styles/pages/auth.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Do not copy the `auth.css` dark mode range (`535-698`); Task 1 already moves that code into `themes/dark/auth.css`.
- Keep only `@keyframes slideUp` inside `animations.css` so the animation definition stays decoupled from layout and form structure.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/pages/auth' | Out-Null`
Expected: `frontend/src/styles/pages/auth` exists.

- [ ] **Write `frontend/src/styles/pages/auth/layout.css`**

```css
/* ============================================
   Authentication Pages
   ============================================ */

.auth-root {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(185, 213, 255, 0.48), transparent 32%),
    linear-gradient(180deg, #eef4ff 0%, #f5f8fc 100%);
}

.theme-toggle {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: var(--z-fixed);
  padding: 10px 14px;
  border-radius: 999px;
  border: 1px solid rgba(166, 184, 214, 0.5);
  background: rgba(255, 255, 255, 0.88);
  color: var(--text-secondary);
  backdrop-filter: blur(14px);
  font-weight: 600;
  transition: all 0.2s ease;
}

.theme-toggle:hover {
  border-color: rgba(59, 102, 224, 0.3);
  color: var(--text-primary);
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(76, 96, 130, 0.12);
}

.auth-card {
  width: min(1024px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(220, 228, 242, 0.9);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 30px 70px rgba(91, 113, 150, 0.16);
  animation: slideUp 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.change-password-card {
  grid-template-columns: 1fr 1fr;
}

.forgot-password-card {
  grid-template-columns: 0.98fr 1.02fr;
}

.auth-intro {
  position: relative;
  padding: 48px 46px;
  background: linear-gradient(180deg, #cceff7 0%, #bfeaf2 100%);
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.auth-intro .badge {
  width: fit-content;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
  letter-spacing: 0.01em;
  box-shadow: 0 8px 20px rgba(121, 149, 194, 0.12);
}

.auth-intro h1 {
  margin: 0;
  font-size: clamp(42px, 4vw, 58px);
  font-weight: 800;
  color: #0f1f47;
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.auth-intro p {
  margin: 0;
  max-width: 440px;
  font-size: 18px;
  color: rgba(15, 31, 71, 0.82);
  line-height: 1.72;
}

.auth-intro-copy {
  display: grid;
  gap: 18px;
}

.auth-intro-primary {
  justify-content: space-between;
}

.auth-intro-support,
.auth-intro-security {
  justify-content: center;
}

.badge-success {
  color: #0f766e;
  background: rgba(240, 253, 250, 0.82);
}

.auth-feature-stack {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 18px;
  margin-top: 6px;
}

.auth-feature-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 74px;
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(220, 228, 242, 0.95);
  border-radius: 18px;
  box-shadow: 0 14px 30px rgba(126, 149, 178, 0.16);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  color: #0f1f47;
  font-size: 17px;
  font-weight: 700;
}

.auth-feature-card:hover {
  transform: translateX(4px);
  box-shadow: 0 18px 34px rgba(126, 149, 178, 0.2);
  border-color: rgba(80, 122, 235, 0.28);
}

.auth-feature-icon {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: #eef3ff;
  flex-shrink: 0;
}

.auth-feature-icon svg {
  width: 22px;
  height: 22px;
  fill: currentColor;
}

.auth-feature-icon-purple {
  color: #5b5bf4;
  background: rgba(92, 92, 244, 0.12);
}

.auth-feature-icon-blue {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.12);
}

.auth-feature-icon-amber {
  color: #ea7a13;
  background: rgba(234, 122, 19, 0.14);
}

.auth-intro-orb {
  position: absolute;
  right: -44px;
  bottom: -54px;
  border-radius: 50%;
  pointer-events: none;
}

.auth-intro-orb-large {
  width: 250px;
  height: 250px;
  background: rgba(135, 225, 245, 0.3);
}

.auth-intro-orb-small {
  width: 160px;
  height: 160px;
  right: 24px;
  bottom: -34px;
  background: rgba(157, 235, 250, 0.48);
}

.auth-info-panel {
  position: relative;
  z-index: 1;
  padding: 22px 24px;
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 20px;
  box-shadow: 0 14px 30px rgba(126, 149, 178, 0.12);
}

.auth-info-panel h3 {
  margin: 0 0 14px;
  font-size: 18px;
  font-weight: 700;
  color: #0f1f47;
}
```

- [ ] **Write `frontend/src/styles/pages/auth/login-form.css`**

```css
.auth-form {
  padding: 52px 48px;
  background: rgba(255, 255, 255, 0.98);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.auth-form-header {
  margin-bottom: 14px;
}

.auth-form h2 {
  margin: 0 0 8px;
  font-size: clamp(28px, 2vw, 40px);
  font-weight: 800;
  color: #0f1f47;
  letter-spacing: -0.03em;
}

.auth-form-subtitle {
  margin: 0;
  font-size: 16px;
  color: #6d7c9a;
  line-height: 1.6;
}

.auth-input-shell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 56px;
  padding: 0 16px;
  background: #f8fbff;
  border: 1px solid #d9e3f2;
  border-radius: 16px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.auth-input-shell:focus-within {
  border-color: rgba(59, 102, 224, 0.65);
  box-shadow: 0 0 0 4px rgba(59, 102, 224, 0.1);
  background: #fff;
}

.auth-input-icon {
  width: 18px;
  height: 18px;
  color: #9aa7c0;
  flex-shrink: 0;
}

.auth-input-icon svg {
  width: 100%;
  height: 100%;
  fill: currentColor;
}

.auth-input-shell input {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.auth-input-shell input:hover,
.auth-input-shell input:focus {
  border: 0;
  box-shadow: none;
  background: transparent;
}

.security-tips,
.steps-list {
  margin: 0;
  padding-left: 18px;
  color: #4f6286;
  font-size: 14px;
  line-height: 1.8;
}

.security-tips li,
.steps-list li {
  margin-bottom: 8px;
}

.password-requirements {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.password-requirements li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.48);
  color: #4f6286;
}

.password-requirements li.requirement-met,
.requirement-item.met {
  color: #176b5e;
  background: rgba(238, 253, 248, 0.78);
}

.requirement-icon {
  font-size: 15px;
  font-weight: 700;
  width: 18px;
  text-align: center;
}

.help-options {
  display: grid;
  gap: 16px;
  margin: 0;
}

.help-option {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: #f8fbff;
  border: 1px solid #dbe5f2;
  border-radius: 18px;
  transition: all 0.2s ease;
}

.help-option:hover {
  border-color: #bfd0ee;
  box-shadow: 0 14px 28px rgba(151, 166, 194, 0.12);
  transform: translateY(-1px);
}

.help-option-copy {
  display: grid;
  gap: 6px;
}

.help-option h4 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f1f47;
}

.help-option p {
  margin: 0;
  font-size: 14px;
  color: #617393;
  line-height: 1.6;
}

.help-option button {
  width: 100%;
}

.divider {
  margin: 28px 0 18px;
  text-align: center;
  position: relative;
}

.divider::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 1px;
  background: var(--border-light);
}

.divider span {
  position: relative;
  background: #fff;
  padding: 0 16px;
  font-size: 13px;
  color: #9aa7c0;
  font-weight: 500;
}

.social-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 8px;
}

.social-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 54px;
  padding: 0 16px;
  border: 1px solid #d8e1ef;
  border-radius: 16px;
  background: #fff;
  color: #17305e;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 8px 16px rgba(151, 166, 194, 0.1);
}

.social-btn:hover {
  background: #f9fbff;
  border-color: #b8caec;
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(151, 166, 194, 0.14);
}

.social-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
```

- [ ] **Write `frontend/src/styles/pages/auth/register-form.css`**

```css
.social-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  font-size: 19px;
  font-weight: 700;
}

.social-icon svg {
  width: 100%;
  height: 100%;
  fill: currentColor;
}

.social-icon-google {
  color: #4285f4;
}

.social-icon-github {
  color: #1f2937;
}

.footer-text {
  margin: 0 0 6px;
  font-size: 13px;
  color: #9aa7c0;
  text-align: center;
}

.auth-extra-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 6px;
}

.auth-checkline {
  margin: 0;
}

.auth-footer {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid #e7edf6;
  text-align: center;
}

.auth-footer .text-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #3467ea;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.auth-footer .text-link:hover {
  color: #274fbc;
  text-decoration: underline;
}

.action-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.action-grid > * {
  min-height: 54px;
}

.auth-secondary-btn {
  font-weight: 700;
}
```

- [ ] **Write `frontend/src/styles/pages/auth/animations.css`**

```css
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify login, register, forgot-password, and change-password screens, including card layout, input shells, social actions, and entry animation.

- [ ] **Commit**

```bash
git add frontend/src/styles/pages/auth/layout.css frontend/src/styles/pages/auth/login-form.css frontend/src/styles/pages/auth/register-form.css frontend/src/styles/pages/auth/animations.css
git commit -m "refactor(css): split auth page styles into layout and form modules"
```

### Task 4: Split `forms.css` into `components/forms/`

**Files:**
- Create: `frontend/src/styles/components/forms/inputs.css` from `frontend/src/styles/components/forms.css:1-55,70-135`
- Create: `frontend/src/styles/components/forms/selects.css` from `frontend/src/styles/components/forms.css:56-68`
- Create: `frontend/src/styles/components/forms/toggles.css` from `frontend/src/styles/components/forms.css:154-233,317-403`
- Create: `frontend/src/styles/components/forms/validation.css` from `frontend/src/styles/components/forms.css:136-153`
- Source: `frontend/src/styles/components/forms.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Do not leave the `composer-main textarea` block in the forms split; move source lines `234-315` in Task 6 to `features/composer/input-area.css`.
- Keep both toggle definitions together in `toggles.css` and preserve their original order to avoid visual regressions.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/components/forms' | Out-Null`
Expected: `frontend/src/styles/components/forms` exists.

- [ ] **Write `frontend/src/styles/components/forms/inputs.css`**

```css
/* ============================================
   Forms Component
   Consolidated from: components.css, precision-adjustments.css
   ============================================ */

/* ============================================
   Base Input Styles
   ============================================ */

input,
textarea,
select {
  width: 100%;
  padding: 0.625rem 0;
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--surface);
  border: 1.5px solid var(--border-light);
  border-radius: 10px;
  transition: all 0.2s ease;
  outline: none;
  line-height: 1.5;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

input:hover,
textarea:hover,
select:hover {
  border-color: var(--border-medium);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

input:focus,
textarea:focus,
select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light), 0 1px 2px rgba(0, 0, 0, 0.05);
  background: var(--surface);
}

input::placeholder,
textarea::placeholder {
  color: var(--text-tertiary);
}

/* ============================================
   Textarea
   ============================================ */

textarea {
  resize: vertical;
  min-height: 100px;
  font-family: inherit;
}

/* ============================================
   Input Group
   ============================================ */

.input-group {
  margin-bottom: 22px;
}

.input-group label {
  display: block;
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 700;
  color: #0f1f47;
}

/* ============================================
   Auth Input Shell
   ============================================ */

.auth-input-shell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 56px;
  padding: 0 16px;
  background: #f8fbff;
  border: 1px solid #d9e3f2;
  border-radius: 16px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.auth-input-shell:focus-within {
  border-color: rgba(59, 102, 224, 0.65);
  box-shadow: 0 0 0 4px rgba(59, 102, 224, 0.1);
  background: #fff;
}

.auth-input-icon {
  width: 18px;
  height: 18px;
  color: #9aa7c0;
  flex-shrink: 0;
}

.auth-input-icon svg {
  width: 100%;
  height: 100%;
  fill: currentColor;
}

.auth-input-shell input {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.auth-input-shell input:hover,
.auth-input-shell input:focus {
  border: 0;
  box-shadow: none;
  background: transparent;
}
```

- [ ] **Write `frontend/src/styles/components/forms/selects.css`**

```css
/* ============================================
   Select
   ============================================ */

select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
  background-position: right var(--space-3) center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: var(--space-10);
}
```

- [ ] **Write `frontend/src/styles/components/forms/toggles.css`**

```css
/* ============================================
   Checkbox
   ============================================ */

.checkline {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--text-sm);
  color: #52627d;
}

.checkline input[type="checkbox"] {
  width: 17px;
  height: 17px;
  margin: 0;
  cursor: pointer;
  accent-color: var(--accent);
  box-shadow: none;
}

/* ============================================
   Toggle Switch (from precision-adjustments.css)
   iOS/Vercel Style Toggle
   ============================================ */

.option-chip {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  padding: 0;
  border: none;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  font-size: 0;
  color: transparent;
}

/* Toggle slider */
.option-chip::before {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Hover state */
.option-chip:hover {
  background: rgba(0, 0, 0, 0.2);
  transform: none;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.15);
}

/* Active state - ON */
.option-chip.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.2);
}

.option-chip.active::before {
  left: 25px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.option-chip.active:hover {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.2);
}

/* ============================================
   Toggle Switch - iOS/Vercel Style
   Migrated from: overrides.css
   ============================================ */

.option-chip {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  padding: 0;
  border: none;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  font-size: 0;
  color: transparent;
}

.option-chip::before {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: #ffffff;
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.option-chip:hover {
  background: rgba(0, 0, 0, 0.2);
  transform: none;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.15);
}

.option-chip.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.2);
}

.option-chip.active::before {
  left: 25px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.option-chip.active:hover {
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.2);
}

:root[data-theme="dark"] .option-chip {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .option-chip::before {
  background: #e2e8f0;
}

:root[data-theme="dark"] .option-chip:hover {
  background: rgba(255, 255, 255, 0.15);
}

/* ============================================
   Responsive Adjustments
   ============================================ */

@media (max-width: 768px) {
  .option-chip {
    width: 44px;
    height: 24px;
  }

  .option-chip::before {
    width: 18px;
    height: 18px;
  }

  .option-chip.active::before {
    left: 23px;
  }
```

- [ ] **Write `frontend/src/styles/components/forms/validation.css`**

```css
/* ============================================
   Hint Text
   ============================================ */

.hint {
  margin-top: 10px;
  font-size: 13px;
  color: #95a0b6;
}

.hint.ok {
  color: #4b6cb7;
}

.hint.error {
  color: #d34f4f;
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify auth inputs, selects, checkbox, toggle, hint text, and confirm the composer textarea still renders correctly after its cross-module move.

- [ ] **Commit**

```bash
git add frontend/src/styles/components/forms/inputs.css frontend/src/styles/components/forms/selects.css frontend/src/styles/components/forms/toggles.css frontend/src/styles/components/forms/validation.css
git commit -m "refactor(css): split shared form styles into focused modules"
```

### Task 5: Split `sidebar.css` into `components/navigation/`

**Files:**
- Create: `frontend/src/styles/components/navigation/sidebar-structure.css` from `frontend/src/styles/components/sidebar.css:1-261`
- Create: `frontend/src/styles/components/navigation/sidebar-items.css` from `frontend/src/styles/components/sidebar.css:262-365`
- Create: `frontend/src/styles/components/navigation/sidebar-states.css` from `frontend/src/styles/components/sidebar.css:366-430`
- Source: `frontend/src/styles/components/sidebar.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Import `sidebar-structure.css` before `sidebar-items.css` so the container layout loads before session/item styling.
- Keep collapsed rail rules and responsive sidebar rules together in `sidebar-states.css`.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/components/navigation' | Out-Null`
Expected: `frontend/src/styles/components/navigation` exists.

- [ ] **Write `frontend/src/styles/components/navigation/sidebar-structure.css`**

```css
/* ============================================
   Sidebar Component
   Consolidated from: sidebar.css
   ============================================ */

/* ============================================
   Sidebar Layout
   ============================================ */

.page-shell.sidebar-collapsed {
  grid-template-columns: 76px minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.sidebar-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 0;
  flex: 1;
}

/* ============================================
   Sidebar Header
   ============================================ */

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-brand-block {
  display: grid;
  gap: 6px;
}

.sidebar-brand-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(94, 168, 255, 0.12);
  border: 1px solid rgba(94, 168, 255, 0.16);
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sidebar-header .brand {
  font-size: 28px;
  line-height: 1;
  letter-spacing: -0.03em;
}

.sidebar-header .muted {
  max-width: 220px;
  color: var(--text-tertiary);
  line-height: 1.55;
}

.sidebar-collapse-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(156, 180, 205, 0.14);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  box-shadow: none;
}

.sidebar-collapse-btn:hover {
  background: rgba(108, 182, 255, 0.12);
  border-color: rgba(108, 182, 255, 0.28);
  color: var(--text-primary);
}

/* ============================================
   Sidebar Groups
   ============================================ */

.sidebar-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px;
}

.sidebar-group-title span {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.sidebar-group-title-with-action {
  gap: 0.8rem;
}

.sidebar-group-action {
  border: 1px solid rgba(121, 169, 255, 0.18);
  background: rgba(121, 169, 255, 0.04);
  color: var(--text-secondary);
  border-radius: 999px;
  padding: 0.32rem 0.72rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  transition: background 180ms ease, border-color 180ms ease, color 180ms ease, transform 180ms ease;
}

.sidebar-group-action:hover {
  background: rgba(121, 169, 255, 0.11);
  border-color: rgba(121, 169, 255, 0.28);
  color: var(--text-primary);
  transform: translateY(-1px);
}

/* ============================================
   Sidebar History
   ============================================ */

.sidebar-history {
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 40vh;
}

.sidebar-history-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sidebar-history-panel .session-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}

/* ============================================
   Sidebar Tools
   ============================================ */

.sidebar-tools {
  min-height: 0;
  flex: 1;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 12px;
  padding-right: 4px;
}

/* ============================================
   Sidebar Module
   ============================================ */

.sidebar-module {
  margin-top: 0;
  padding: 0;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(145, 172, 204, 0.14);
  background: linear-gradient(180deg, rgba(18, 33, 48, 0.92), rgba(14, 27, 40, 0.98));
}

.sidebar-module-toggle {
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px 13px;
  background: transparent;
  border: 0;
  border-radius: 0;
  color: var(--text-primary);
  box-shadow: none;
}

.sidebar-module-copy {
  display: grid;
  gap: 4px;
  text-align: left;
}

.sidebar-module-toggle strong {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.sidebar-module-copy small {
  color: var(--text-tertiary);
  font-size: 12px;
  line-height: 1.45;
}

.sidebar-module-meta {
  display: grid;
  justify-items: end;
  gap: 6px;
  flex-shrink: 0;
}

.sidebar-module-meta em {
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: rgba(95, 161, 237, 0.12);
  border: 1px solid rgba(95, 161, 237, 0.14);
  border-radius: 999px;
  padding: 3px 8px;
}

.sidebar-module-toggle span {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
}

.sidebar-module-body {
  padding: 0 16px 16px;
}

.sidebar-module-body > .panel {
  margin-top: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
}

.sidebar-module-body > .panel > .section-head {
  display: none;
}

.sidebar-module-body > .panel:hover {
  box-shadow: none;
}
```

- [ ] **Write `frontend/src/styles/components/navigation/sidebar-items.css`**

```css
/* ============================================
   Sidebar Section Head
   ============================================ */

.sidebar-section-head {
  margin-bottom: 2px;
  padding: 0;
}

.sidebar-section-head > div {
  display: grid;
  gap: 2px;
}

.sidebar-section-head strong {
  font-size: 15px;
  color: var(--text-primary);
}

.sidebar-section-head .muted {
  font-size: 12px;
}

/* ============================================
   Session List
   ============================================ */

.session-list {
  gap: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border-radius: 14px;
  background: transparent;
  border: 1px solid transparent;
}

.session-main-btn {
  min-width: 0;
  flex: 1;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(132, 160, 190, 0.12);
  color: var(--text-primary);
  box-shadow: none;
}

.session-main-btn:hover:not(:disabled) {
  transform: none;
  background: rgba(95, 161, 237, 0.1);
  border-color: rgba(95, 161, 237, 0.26);
  box-shadow: none;
}

.session-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 700;
  color: inherit;
}

.session-count {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.session-delete-btn {
  min-width: 36px;
  min-height: 36px;
  padding: 0;
  border-radius: 10px;
  opacity: 0;
  transform: translateX(-4px);
  transition: opacity 160ms ease, transform 160ms ease, background 160ms ease, border-color 160ms ease;
}

.session-item:hover .session-delete-btn,
.session-item.active .session-delete-btn {
  opacity: 1;
  transform: translateX(0);
}

.session-item.active {
  background: rgba(95, 161, 237, 0.08);
  border-color: rgba(95, 161, 237, 0.16);
}

.session-item.active .session-main-btn {
  background: rgba(95, 161, 237, 0.16);
  border-color: rgba(95, 161, 237, 0.28);
}
```

- [ ] **Write `frontend/src/styles/components/navigation/sidebar-states.css`**

```css
/* ============================================
   Sidebar Rail (Collapsed State)
   ============================================ */

.sidebar-rail {
  align-items: center;
  justify-content: space-between;
  padding: 16px 10px;
}

.sidebar-rail-header,
.sidebar-rail-actions {
  display: grid;
  gap: 10px;
}

.sidebar-rail-brand,
.sidebar-rail-btn {
  width: 52px;
  min-height: 52px;
  padding: 0;
  border-radius: 16px;
  border: 1px solid rgba(156, 180, 205, 0.18);
  background: rgba(16, 31, 44, 0.92);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 800;
  box-shadow: none;
}

.sidebar-rail-brand {
  font-size: 20px;
}

.sidebar-rail-brand:hover,
.sidebar-rail-btn:hover {
  border-color: rgba(108, 182, 255, 0.4);
  background: rgba(24, 43, 64, 0.98);
}

.page-shell.sidebar-collapsed .main {
  min-width: 0;
}

/* ============================================
   Responsive Adjustments
   ============================================ */

@media (max-width: 1080px) {
  .page-shell.sidebar-collapsed {
    grid-template-columns: 1fr;
  }

  .sidebar-shell {
    height: 100%;
  }

  .sidebar-history {
    max-height: 34vh;
  }

  .sidebar-collapse-btn {
    display: none;
  }
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify expanded/collapsed sidebar states, session history list, rail view, and the layout below `1080px`.

- [ ] **Commit**

```bash
git add frontend/src/styles/components/navigation/sidebar-structure.css frontend/src/styles/components/navigation/sidebar-items.css frontend/src/styles/components/navigation/sidebar-states.css
git commit -m "refactor(css): split sidebar styles into navigation modules"
```

### Task 6: Split `composer.css` into `features/composer/`

**Files:**
- Create: `frontend/src/styles/features/composer/input-area.css` from `frontend/src/styles/features/composer.css:1-100,353-363 + frontend/src/styles/components/forms.css:234-315`
- Create: `frontend/src/styles/features/composer/quick-prompts.css` from `frontend/src/styles/features/composer.css:188-246,399-406`
- Create: `frontend/src/styles/features/composer/actions.css` from `frontend/src/styles/features/composer.css:101-187,247-352,364-398`
- Source: `frontend/src/styles/features/composer.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Append the composer textarea block from `frontend/src/styles/components/forms.css:234-315` to `input-area.css` so the textarea styling lives with the feature that owns it.
- Keep the quick prompt scroll hint and mobile quick prompt rules inside the quick prompts file rather than mixing them into actions.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/features/composer' | Out-Null`
Expected: `frontend/src/styles/features/composer` exists.

- [ ] **Write `frontend/src/styles/features/composer/input-area.css`**

```css
/* ============================================
   FEATURE: Chat Composer Panel
   Extracted from: chat-workbench.css, final-polish.css
   ============================================ */

/* Composer Panel */
.composer-panel {
  margin-top: 0;
  border: 2px solid rgba(0, 0, 0, 0.08);
  border-radius: 16px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.1), 0 4px 8px -4px rgba(0, 0, 0, 0.06);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.composer-panel::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 16px;
  padding: 2px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.15));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.composer-panel:hover {
  border-color: rgba(102, 126, 234, 0.2);
  box-shadow: 0 12px 32px -8px rgba(102, 126, 234, 0.15), 0 4px 12px -4px rgba(0, 0, 0, 0.08);
}

.composer-panel:hover::before {
  opacity: 0.6;
}

.composer-panel:focus-within {
  border-color: rgba(102, 126, 234, 0.4);
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.12), 0 12px 32px -8px rgba(102, 126, 234, 0.2);
}

.composer-panel:focus-within::before {
  opacity: 1;
}

.composer-panel.dragover {
  outline: 3px dashed rgba(102, 126, 234, 0.5);
  outline-offset: 6px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
  border-color: rgba(102, 126, 234, 0.4);
  transform: scale(1.01);
}

/* Composer Main */
.composer-main {
  display: grid;
  gap: 8px;
}

.composer-label {
  color: #64748b;
  font-family: "Geist Mono", "Cascadia Code", monospace;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Composer Textarea */
.composer-panel textarea {
  min-height: 96px;
  border: 0;
  border-radius: 12px;
  padding: 12px 0;
  margin-top: 0;
  background: transparent;
  font-size: 15px;
  line-height: 1.6;
  resize: vertical;
  transition: all 0.2s ease;
  color: var(--work-text);
}

.composer-panel textarea:focus {
  outline: none;
}

.composer-panel textarea::placeholder {
  color: #94a3b8;
  font-size: 15px;
}

/* Responsive */
@media (max-width: 860px) {
  .composer-panel {
    padding: 10px;
    border-radius: 10px;
  }

  .composer-panel textarea {
    min-height: 80px;
    font-size: 15px;
  }
```

Append this cross-source block to `frontend/src/styles/features/composer/input-area.css`, extracted from `frontend/src/styles/components/forms.css:234-315`:
```css
/* ============================================
   Composer Textarea (from precision-adjustments.css)
   Enhanced textarea with gradient background
   ============================================ */

.composer-main textarea {
  border: 2px solid rgba(0, 0, 0, 0.15);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  font-size: 15px;
  line-height: 1.7;
  color: #0f172a;
  padding: 14px 18px;
  min-height: 120px;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.composer-main textarea::placeholder {
  color: #94a3b8;
  opacity: 0.9;
}

.composer-main textarea:hover {
  border-color: rgba(0, 0, 0, 0.2);
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

/* Focus state with soft glow */
.composer-main textarea:focus {
  outline: none;
  border-color: rgba(102, 126, 234, 0.8);
  background: #ffffff;
  box-shadow:
    0 0 0 4px rgba(102, 126, 234, 0.12),
    0 0 0 8px rgba(102, 126, 234, 0.06),
    0 4px 12px rgba(102, 126, 234, 0.15),
    inset 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* ============================================
   Dark Mode Overrides
   ============================================ */

:root[data-theme="dark"] .option-chip {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .option-chip::before {
  background: #e2e8f0;
}

:root[data-theme="dark"] .option-chip:hover {
  background: rgba(255, 255, 255, 0.15);
}

:root[data-theme="dark"] .composer-main textarea {
  border-color: rgba(255, 255, 255, 0.15);
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.9));
  color: #f1f5f9;
}

:root[data-theme="dark"] .composer-main textarea::placeholder {
  color: #64748b;
}

:root[data-theme="dark"] .composer-main textarea:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(51, 65, 85, 0.95));
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

:root[data-theme="dark"] .composer-main textarea:focus {
  border-color: rgba(102, 126, 234, 0.8);
  background: rgba(15, 23, 42, 1);
  box-shadow:
    0 0 0 4px rgba(102, 126, 234, 0.2),
    0 0 0 8px rgba(102, 126, 234, 0.1),
    0 4px 12px rgba(102, 126, 234, 0.25),
    inset 0 1px 2px rgba(0, 0, 0, 0.3);
}
```

- [ ] **Write `frontend/src/styles/features/composer/quick-prompts.css`**

```css
/* Quick Prompt Row */
.quick-prompt-row {
  position: relative;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.quick-prompt-row::-webkit-scrollbar {
  display: none;
}

/* Scroll hint gradient - migrated from overrides.css */
.quick-prompt-row::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 40px;
  background: linear-gradient(90deg, transparent, var(--surface));
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s;
}

.quick-prompt-row:hover::after {
  opacity: 1;
}

:root[data-theme="dark"] .quick-prompt-row::after {
  background: linear-gradient(90deg, transparent, rgba(30, 41, 59, 0.9));
}

.quick-prompt-row .tiny-btn {
  border-radius: 999px;
  color: #475569;
  background: #ffffff;
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.quick-prompt-row .tiny-btn:hover {
  border-color: rgba(102, 126, 234, 0.3);
  background: #fafbfc;
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(102, 126, 234, 0.15);
  color: #667eea;
}

  .quick-prompt-row {
    gap: 6px;
  }

  .quick-prompt-row .tiny-btn {
    font-size: 12px;
    padding: 6px 10px;
  }
```

- [ ] **Write `frontend/src/styles/features/composer/actions.css`**

```css
/* Composer Actions */
.composer-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.primary-action {
  min-width: 140px;
  min-height: 44px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 12px;
  font-weight: 700;
  font-size: 15px;
  color: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35), 0 2px 4px rgba(102, 126, 234, 0.2);
  position: relative;
  overflow: hidden;
}

.primary-action::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.primary-action:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.45), 0 4px 8px rgba(102, 126, 234, 0.25);
}

.primary-action:hover:not(:disabled)::before {
  opacity: 1;
}

.primary-action:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
}

.primary-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.composer-actions button.secondary,
.composer-actions .link-btn {
  min-height: 40px;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  background: #ffffff;
  border: 1.5px solid rgba(0, 0, 0, 0.1);
  color: #475569;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.composer-actions button.secondary:hover,
.composer-actions .link-btn:hover {
  border-color: rgba(102, 126, 234, 0.3);
  background: #fafbfc;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.composer-actions button.danger {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: none;
  color: white;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.35);
}

.composer-actions button.danger:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.45);
}

/* Chat Options Bar */
.chat-options-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.06);
  margin-top: 10px;
  transition: all 0.2s ease;
}

.chat-options-bar:hover {
  background: rgba(248, 250, 252, 0.9);
  border-color: rgba(102, 126, 234, 0.15);
}

.option-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-label {
  color: #64748b;
  font-family: "Geist Mono", "Cascadia Code", monospace;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.option-chip {
  min-width: 60px;
  min-height: 32px;
  padding: 6px 14px;
  border-radius: 999px;
  background: #ffffff;
  border: 1.5px solid rgba(0, 0, 0, 0.1);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.option-chip:hover {
  border-color: rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.15);
  background: #ffffff;
}

.option-chip.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
  font-weight: 700;
}

.option-chip.active:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.option-agent select {
  height: 36px;
  border-radius: 10px;
  background: #ffffff;
  border: 1.5px solid rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.option-agent select:hover {
  border-color: rgba(102, 126, 234, 0.4);
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.15);
}

.option-agent select:focus {
  border-color: rgba(102, 126, 234, 0.6);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.12);
  outline: none;
}

.option-hint {
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
  padding: 8px 12px;
  background: rgba(248, 250, 252, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

  .chat-options-bar {
    padding: 10px;
    gap: 10px;
  }

  .option-chip {
    min-width: 56px;
    min-height: 36px;
    padding: 6px 12px;
    font-size: 13px;
  }

  .option-agent select {
    height: 36px;
    font-size: 13px;
  }

  .primary-action {
    min-width: 100%;
    min-height: 48px;
    font-size: 15px;
  }

  .composer-actions {
    flex-direction: column;
    gap: 8px;
  }

  .composer-actions button.secondary,
  .composer-actions .link-btn {
    width: 100%;
    justify-content: center;
  }
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify the composer input area, dragover state, action buttons, quick prompt row, option bar, and mobile button stacking.

- [ ] **Commit**

```bash
git add frontend/src/styles/features/composer/input-area.css frontend/src/styles/features/composer/quick-prompts.css frontend/src/styles/features/composer/actions.css
git commit -m "refactor(css): split composer feature styles into input prompt and action files"
```

### Task 7: Split `buttons.css` into `components/buttons/`

**Files:**
- Create: `frontend/src/styles/components/buttons/base.css` from `frontend/src/styles/components/buttons.css:1-170`
- Create: `frontend/src/styles/components/buttons/variants.css` from `frontend/src/styles/components/buttons.css:171-244,336-342`
- Create: `frontend/src/styles/components/buttons/effects.css` from `frontend/src/styles/components/buttons.css:245-364`
- Source: `frontend/src/styles/components/buttons.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Preserve the base -> variants -> effects import order so the original cascade remains intact and `effects.css` still lands last.
- Keep the help option button width rule in `variants.css` so it is not accidentally overridden by the composer interaction styles in `effects.css`.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/components/buttons' | Out-Null`
Expected: `frontend/src/styles/components/buttons` exists.

- [ ] **Write `frontend/src/styles/components/buttons/base.css`**

```css
/* ============================================
   Buttons Component
   Consolidated from: components.css, modern-ui-enhancements.css, final-polish.css
   ============================================ */

/* ============================================
   Base Button Styles
   ============================================ */

button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 0.625rem var(--space-6);
  font-size: var(--text-base);
  font-weight: 600;
  border: 1.5px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;
  white-space: nowrap;
  line-height: 1.5;
  user-select: none;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* ============================================
   Primary Button
   ============================================ */

.primary-action-btn,
button:not([class]) {
  background: linear-gradient(135deg, #2f63e6 0%, #356af0 100%);
  color: var(--text-inverse);
  border-color: #2f63e6;
  box-shadow: 0 14px 24px rgba(47, 99, 230, 0.24);
}

.primary-action-btn:hover:not(:disabled),
button:not([class]):hover:not(:disabled) {
  background: linear-gradient(135deg, #264fbc 0%, #315fda 100%);
  transform: translateY(-2px);
  box-shadow: 0 18px 28px rgba(47, 99, 230, 0.28);
}

.primary-action-btn:active:not(:disabled),
button:not([class]):active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* ============================================
   Secondary Button
   ============================================ */

.secondary,
button.secondary {
  background: #fff;
  color: #17305e;
  border-color: #d8e1ef;
  box-shadow: 0 8px 16px rgba(151, 166, 194, 0.1);
}

.secondary:hover:not(:disabled),
button.secondary:hover:not(:disabled) {
  background: #f9fbff;
  border-color: #b8caec;
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(151, 166, 194, 0.14);
}

.secondary:active:not(:disabled),
button.secondary:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* ============================================
   Danger Button
   ============================================ */

.danger,
button.danger {
  background: linear-gradient(135deg, var(--danger) 0%, #c53030 100%);
  color: var(--text-inverse);
  border-color: var(--danger);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.danger:hover:not(:disabled),
button.danger:hover:not(:disabled) {
  background: linear-gradient(135deg, #c53030 0%, var(--danger) 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.danger:active:not(:disabled),
button.danger:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* ============================================
   Tiny Button
   ============================================ */

.tiny-btn {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: 500;
}

/* ============================================
   Text Link Button
   ============================================ */

.text-link-btn {
  padding: 0;
  background: transparent;
  border: none;
  color: #3467ea;
  font-size: var(--text-sm);
  font-weight: 600;
  text-decoration: none;
  box-shadow: none;
}

.text-link-btn:hover {
  color: #274fbc;
  text-decoration: underline;
}

/* ============================================
   Link Button
   ============================================ */

.link-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 54px;
  padding: 0 20px;
  background: #fff;
  border: 1px solid #d8e1ef;
  border-radius: 16px;
  color: #17305e;
  text-decoration: none;
  font-size: 15px;
  font-weight: 600;
  transition: all var(--transition-fast);
  box-shadow: 0 8px 16px rgba(151, 166, 194, 0.1);
}

.link-button:hover {
  background: #f9fbff;
  border-color: #b8caec;
  transform: translateY(-1px);
}
```

- [ ] **Write `frontend/src/styles/components/buttons/variants.css`**

```css
/* ============================================
   Social Button
   ============================================ */

.social-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 54px;
  padding: 0 16px;
  border: 1px solid #d8e1ef;
  border-radius: 16px;
  background: #fff;
  color: #17305e;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 8px 16px rgba(151, 166, 194, 0.1);
}

.social-btn:hover {
  background: #f9fbff;
  border-color: #b8caec;
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(151, 166, 194, 0.14);
}

.social-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* ============================================
   Row Actions Buttons (from modern-ui-enhancements.css)
   ============================================ */

.row-actions .tiny-btn {
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 8px;
  border: 1.5px solid rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
}

.row-actions .tiny-btn.secondary {
  color: #64748b;
  border-color: rgba(100, 116, 139, 0.2);
}

.row-actions .tiny-btn.secondary:hover {
  color: #667eea;
  border-color: rgba(102, 126, 234, 0.4);
  background: rgba(102, 126, 234, 0.08);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
}

.row-actions .tiny-btn.danger {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}

.row-actions .tiny-btn.danger:hover {
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

/* ============================================
   Help Option Buttons
   ============================================ */

.help-option button {
  width: 100%;
}
```

- [ ] **Write `frontend/src/styles/components/buttons/effects.css`**

```css
/* ============================================
   Composer Actions Buttons (from final-polish.css)
   Enhanced with overlay effect from overrides.css
   ============================================ */

.composer-actions .primary-action {
  position: relative;
  overflow: hidden;
  padding: 12px 32px;
  font-size: 15px;
  font-weight: 800;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.4), 0 2px 6px rgba(0, 0, 0, 0.1);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.composer-actions .primary-action::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2), transparent);
  opacity: 0;
  transition: opacity 0.25s;
}

.composer-actions .primary-action:hover::before {
  opacity: 1;
}

.composer-actions .primary-action:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(102, 126, 234, 0.5), 0 4px 12px rgba(0, 0, 0, 0.15);
}

.composer-actions .secondary,
.composer-actions .link-btn {
  padding: 11px 22px;
  font-size: 14px;
  font-weight: 700;
  border: 2px solid rgba(0, 0, 0, 0.15);
  background: #ffffff;
  color: #475569;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.composer-actions .secondary:hover,
.composer-actions .link-btn:hover {
  border-color: rgba(102, 126, 234, 0.4);
  background: rgba(102, 126, 234, 0.05);
  color: #667eea;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
}

.composer-actions .danger {
  border-color: rgba(239, 68, 68, 0.4);
  color: #dc2626;
  font-weight: 700;
}

.composer-actions .danger:hover {
  border-color: rgba(239, 68, 68, 0.6);
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.25);
}

/* ============================================
   Quick Prompt Buttons (from final-polish.css)
   ============================================ */

.quick-prompt-row .tiny-btn {
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 600;
  border: 1.5px solid rgba(102, 126, 234, 0.2);
  background: rgba(102, 126, 234, 0.05);
  color: #667eea;
  opacity: 0.9;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.quick-prompt-row .tiny-btn:hover {
  opacity: 1;
  border-color: rgba(102, 126, 234, 0.4);
  background: rgba(102, 126, 234, 0.1);
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(102, 126, 234, 0.2);
}

/* ============================================
   Help Option Buttons
   ============================================ */

.help-option button {
  width: 100%;
}

/* ============================================
   Dark Mode Overrides
   ============================================ */

:root[data-theme="dark"] .link-button {
  background: rgba(30, 41, 59, 0.8);
  border-color: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
}

:root[data-theme="dark"] .link-button:hover {
  background: rgba(51, 65, 85, 0.9);
  border-color: rgba(255, 255, 255, 0.2);
}

:root[data-theme="dark"] .composer-actions .secondary,
:root[data-theme="dark"] .composer-actions .link-btn {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(30, 41, 59, 0.8);
  color: #cbd5e1;
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify primary, secondary, danger, link, social, tiny, composer action, and quick prompt buttons in hover and active states.

- [ ] **Commit**

```bash
git add frontend/src/styles/components/buttons/base.css frontend/src/styles/components/buttons/variants.css frontend/src/styles/components/buttons/effects.css
git commit -m "refactor(css): split button styles into base variants and effects"
```

### Task 8: Split `messages.css` into `features/messaging/`

**Files:**
- Create: `frontend/src/styles/features/messaging/message-bubbles.css` from `frontend/src/styles/features/messages.css:1-100`
- Create: `frontend/src/styles/features/messaging/message-metadata.css` from `frontend/src/styles/features/messages.css:102-190`
- Create: `frontend/src/styles/features/messaging/message-actions.css` from `frontend/src/styles/features/messages.css:191-283`
- Source: `frontend/src/styles/features/messages.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Even though the third file is named `message-actions.css`, it currently carries the empty state and responsive rules; do not rename selectors in this phase.
- Keep markdown and code block styling grouped with message metadata so content formatting does not regress.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/features/messaging' | Out-Null`
Expected: `frontend/src/styles/features/messaging` exists.

- [ ] **Write `frontend/src/styles/features/messaging/message-bubbles.css`**

```css
/* ============================================
   FEATURE: Message Bubbles
   Extracted from: chat-workbench.css
   ============================================ */

/* Message Bubbles */
.bubble {
  margin-top: 20px;
  max-width: 100%;
  border-radius: 16px;
  padding: 18px 20px;
  line-height: 1.7;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  overflow-wrap: anywhere;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  animation: bubbleSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes bubbleSlideIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bubble:first-of-type {
  margin-top: 0;
}

.bubble:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
  transform: translateY(-2px);
}

/* User Bubble */
.bubble.user {
  width: min(720px, 92%);
  margin-left: auto;
  border: 1.5px solid rgba(37, 130, 217, 0.2);
  background: linear-gradient(135deg, #f0f7ff 0%, #e6f2ff 100%);
  position: relative;
}

.bubble.user::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  padding: 1px;
  background: linear-gradient(135deg, rgba(37, 130, 217, 0.3), rgba(37, 130, 217, 0.1));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.25s;
}

.bubble.user:hover::before {
  opacity: 1;
}

.bubble.user:hover {
  border-color: rgba(37, 130, 217, 0.4);
  background: linear-gradient(135deg, #e8f3ff 0%, #dbeafe 100%);
}

/* Assistant Bubble */
.bubble.assistant {
  width: min(880px, 98%);
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  position: relative;
}

.bubble.assistant::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px 0 0 16px;
  opacity: 0;
  transition: opacity 0.25s;
}

.bubble.assistant:hover::after {
  opacity: 1;
}

.bubble.assistant:hover {
  border-color: rgba(102, 126, 234, 0.25);
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
}
```

- [ ] **Write `frontend/src/styles/features/messaging/message-metadata.css`**

```css
/* Message Header */
.message-head {
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.message-role {
  color: #475569;
  font-family: "Geist Mono", "Cascadia Code", monospace;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.bubble.user .message-role {
  color: #1e40af;
}

.bubble.assistant .message-role {
  color: #667eea;
}

/* Markdown Content */
.markdown {
  color: var(--work-text);
  font-size: 15px;
  line-height: 1.7;
}

.markdown p {
  margin: 0 0 12px 0;
}

.markdown p:last-child {
  margin-bottom: 0;
}

.markdown h1, .markdown h2, .markdown h3, .markdown h4 {
  margin: 16px 0 10px 0;
  font-weight: 600;
  color: var(--work-text);
}

.markdown h1:first-child, .markdown h2:first-child, .markdown h3:first-child {
  margin-top: 0;
}

.markdown ul, .markdown ol {
  margin: 12px 0;
  padding-left: 24px;
}

.markdown li {
  margin: 6px 0;
}

.markdown code {
  font-family: "Geist Mono", "Cascadia Code", Consolas, monospace;
  font-size: 13px;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 4px;
  color: #e11d48;
}

.markdown pre {
  border-radius: 10px;
  background: #0f172a;
  padding: 16px;
  margin: 12px 0;
  overflow-x: auto;
}

.markdown pre code {
  background: transparent;
  padding: 0;
  color: #e2e8f0;
  font-size: 13px;
}
```

- [ ] **Write `frontend/src/styles/features/messaging/message-actions.css`**

```css
/* Empty Chat State */
.empty-chat-state {
  display: grid;
  place-items: center;
  gap: 16px;
  min-height: 400px;
  align-content: center;
  max-width: 680px;
  margin: 0 auto;
  padding: 40px 20px;
  color: var(--work-muted);
  text-align: center;
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.empty-chat-label {
  border: 1.5px solid rgba(102, 126, 234, 0.25);
  border-radius: 999px;
  padding: 8px 16px;
  color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  font-family: "Geist Mono", "Cascadia Code", monospace;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: default;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.empty-chat-label:hover {
  border-color: rgba(102, 126, 234, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.12));
}

.empty-chat-state h3 {
  margin: 0;
  color: var(--work-text);
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) 0.1s both;
}

.empty-chat-state p {
  max-width: 580px;
  line-height: 1.7;
  font-size: 15px;
  color: var(--work-muted);
  animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) 0.2s both;
}

/* Responsive */
@media (max-width: 860px) {
  .bubble {
    padding: 14px 16px;
    border-radius: 12px;
  }

  .bubble.user {
    width: min(100%, 95%);
  }

  .bubble.assistant {
    width: 100%;
  }

  .empty-chat-state {
    padding: 20px 10px;
    min-height: 300px;
  }

  .empty-chat-state h3 {
    font-size: 24px;
  }
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify user and assistant bubbles, message header, markdown rendering, empty-chat state, and mobile widths.

- [ ] **Commit**

```bash
git add frontend/src/styles/features/messaging/message-bubbles.css frontend/src/styles/features/messaging/message-metadata.css frontend/src/styles/features/messaging/message-actions.css
git commit -m "refactor(css): split messaging styles into bubbles metadata and empty-state modules"
```

### Task 9: Split `cards.css` into `components/cards/`

**Files:**
- Create: `frontend/src/styles/components/cards/base.css` from `frontend/src/styles/components/cards.css:1-57,197-217`
- Create: `frontend/src/styles/components/cards/variants.css` from `frontend/src/styles/components/cards.css:58-115,218-257`
- Create: `frontend/src/styles/components/cards/interactions.css` from `frontend/src/styles/components/cards.css:116-196,258-276`
- Source: `frontend/src/styles/components/cards.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Put shared panel and auth-card structure in `base.css`, card-specific variants in `variants.css`, and pseudo-element or hover/active behavior in `interactions.css`.
- Keep dark mode and mobile rules with `interactions.css` so the final import order still matches the original cascade.

- [ ] **Create the target directory**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles/components/cards' | Out-Null`
Expected: `frontend/src/styles/components/cards` exists.

- [ ] **Write `frontend/src/styles/components/cards/base.css`**

```css
/* ============================================
   Cards Component
   Consolidated from: components.css, final-polish.css, precision-adjustments.css
   ============================================ */

/* ============================================
   Base Panel/Card Styles
   ============================================ */

.panel {
  padding: var(--space-6);
  background: var(--surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-base);
}

.panel:hover {
  box-shadow: var(--shadow-md);
}

/* ============================================
   Auth Card
   ============================================ */

.auth-card {
  width: min(1024px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(220, 228, 242, 0.9);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 30px 70px rgba(91, 113, 150, 0.16);
  animation: slideUp 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.change-password-card {
  grid-template-columns: 1fr 1fr;
}

.forgot-password-card {
  grid-template-columns: 0.98fr 1.02fr;
}

/* ============================================
   Auth Info Panel
   ============================================ */

.auth-info-panel {
  position: relative;
  z-index: 1;
  padding: 22px 24px;
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 20px;
  box-shadow: 0 14px 30px rgba(126, 149, 178, 0.12);
}

.auth-info-panel h3 {
  margin: 0 0 14px;
  font-size: 18px;
  font-weight: 700;
  color: #0f1f47;
}
```

- [ ] **Write `frontend/src/styles/components/cards/variants.css`**

```css
/* ============================================
   Auth Feature Card
   ============================================ */

.auth-feature-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 74px;
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(220, 228, 242, 0.95);
  border-radius: 18px;
  box-shadow: 0 14px 30px rgba(126, 149, 178, 0.16);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  color: #0f1f47;
  font-size: 17px;
  font-weight: 700;
}

.auth-feature-card:hover {
  transform: translateX(4px);
  box-shadow: 0 18px 34px rgba(126, 149, 178, 0.2);
  border-color: rgba(80, 122, 235, 0.28);
}

.auth-feature-icon {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: #eef3ff;
  flex-shrink: 0;
}

.auth-feature-icon svg {
  width: 22px;
  height: 22px;
  fill: currentColor;
}

.auth-feature-icon-purple {
  color: #5b5bf4;
  background: rgba(92, 92, 244, 0.12);
}

.auth-feature-icon-blue {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.12);
}

.auth-feature-icon-amber {
  color: #ea7a13;
  background: rgba(234, 122, 19, 0.14);
}

/* ============================================
   Help Option Card
   ============================================ */

.help-option {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  background: #f8fbff;
  border: 1px solid #dbe5f2;
  border-radius: 18px;
  transition: all 0.2s ease;
}

.help-option:hover {
  border-color: #bfd0ee;
  box-shadow: 0 14px 28px rgba(151, 166, 194, 0.12);
  transform: translateY(-1px);
}

.help-option-copy {
  display: grid;
  gap: 6px;
}

.help-option h4 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f1f47;
}

.help-option p {
  margin: 0;
  font-size: 14px;
  color: #617393;
  line-height: 1.6;
}
```

- [ ] **Write `frontend/src/styles/components/cards/interactions.css`**

```css
/* ============================================
   Agent Mode Card (from precision-adjustments.css & final-polish.css)
   Enhanced with hover animations and active state
   ============================================ */

.agent-mode-card {
  position: relative;
  padding: 18px 16px;
  min-height: 120px;
  border-radius: 12px;
  border: 2px solid rgba(156, 180, 205, 0.15);
  background: rgba(16, 31, 44, 0.8);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
  text-align: left;
}

/* Hover state - background transition animation */
.agent-mode-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.12));
  opacity: 0;
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 0;
}

.agent-mode-card:hover::before {
  opacity: 1;
}

.agent-mode-card:hover {
  border-color: rgba(58, 151, 232, 0.5);
  background: rgba(21, 40, 56, 0.95);
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
}

/* Active state - enhanced background highlight */
.agent-mode-card.active {
  border-color: rgba(102, 126, 234, 0.8);
  background: linear-gradient(135deg, rgba(18, 48, 71, 1), rgba(25, 55, 85, 1));
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4), 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

.agent-mode-card.active::before {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
  opacity: 1;
}

.agent-mode-card.active::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px 0 0 12px;
  box-shadow: 0 0 12px rgba(102, 126, 234, 0.6);
  z-index: 1;
}

.agent-mode-card.active:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(102, 126, 234, 0.5), 0 6px 16px rgba(0, 0, 0, 0.25);
}

/* Ensure content is above pseudo-elements */
.agent-mode-card > * {
  position: relative;
  z-index: 2;
}

/* ============================================
   Dark Mode Overrides
   ============================================ */

:root[data-theme="dark"] .auth-card {
  background: rgba(30, 41, 59, 0.95);
  border-color: rgba(255, 255, 255, 0.1);
}

/* ============================================
   Responsive Adjustments
   ============================================ */

@media (max-width: 768px) {
  .agent-mode-card {
    padding: 16px 14px;
    min-height: 100px;
  }
}
```

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run manual smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify auth cards, feature cards, agent mode cards, and help option cards in hover, active, dark mode, and mobile states.

- [ ] **Commit**

```bash
git add frontend/src/styles/components/cards/base.css frontend/src/styles/components/cards/variants.css frontend/src/styles/components/cards/interactions.css
git commit -m "refactor(css): split card styles into base variants and interactions"
```

### Task 10: Update `main.css`, remove monolith files, and run full regression pass

**Files:**
- Modify: `frontend/src/styles/main.css`
- Test: `frontend/package.json` (`npm run build`, `npm run dev`)

- Replace the legacy `@import` list with the new split-file structure and remove all 9 monolith CSS imports.
- Only remove the old files after `npm run build` succeeds with the new import graph.

- [ ] **Confirm the styles root exists**

Run: `New-Item -ItemType Directory -Force 'frontend/src/styles' | Out-Null`
Expected: `frontend/src/styles` exists.

- [ ] **Write `frontend/src/styles/main.css`**

```css
/* ============================================
   Multi-Agent RAG Local - Main Stylesheet
   Main stylesheet - unified CSS entry point
   ============================================

   IMPORT ORDER (CRITICAL - DO NOT REORDER):
   1. Core Layer - Design tokens, reset, utilities
   2. Theme Layer - Dark mode and theme variants
   3. Component Layer - Reusable UI components
   4. Page Layer - Page-specific layouts
   5. Feature Layer - Feature-specific modules

   ============================================ */

/* ============================================
   LAYER 1: CORE - Foundation
   Design tokens, CSS reset, utility classes
   ============================================ */

@import './core/tokens.css';
@import './core/reset.css';
@import './core/utilities.css';

/* ============================================
   LAYER 2: THEMES - Visual Variants
   Dark mode and theme-specific overrides
   ============================================ */

@import './themes/dark/colors.css';
@import './themes/dark/admin.css';
@import './themes/dark/components.css';
@import './themes/dark/auth.css';
@import './themes/dark/chat.css';
@import './themes/dark/effects.css';

/* ============================================
   LAYER 3: COMPONENTS - Reusable UI Elements
   Buttons, forms, cards, modals, etc.
   Order: Atomic -> Composite
   ============================================ */

/* Atomic Components */
@import './components/buttons/base.css';
@import './components/buttons/variants.css';
@import './components/buttons/effects.css';
@import './components/forms/inputs.css';
@import './components/forms/selects.css';
@import './components/forms/toggles.css';
@import './components/forms/validation.css';
@import './components/badges.css';
@import './components/avatars.css';
@import './components/spinners.css';
@import './components/tooltips.css';

/* Composite Components */
@import './components/cards/base.css';
@import './components/cards/variants.css';
@import './components/cards/interactions.css';
@import './components/modals.css';
@import './components/dropdowns.css';
@import './components/alerts.css';
@import './components/tables.css';
@import './components/navigation/sidebar-structure.css';
@import './components/navigation/sidebar-items.css';
@import './components/navigation/sidebar-states.css';

/* ============================================
   LAYER 4: PAGES - Page-Specific Layouts
   Authentication, chat, admin, profile pages
   ============================================ */

@import './pages/auth/layout.css';
@import './pages/auth/animations.css';
@import './pages/auth/login-form.css';
@import './pages/auth/register-form.css';
@import './pages/chat.css';
@import './pages/admin/layout.css';
@import './pages/admin/dashboard.css';
@import './pages/admin/user-management.css';
@import './pages/admin/system-settings.css';
@import './pages/profile.css';

/* ============================================
   LAYER 5: FEATURES - Feature-Specific Modules
   Messages, composer, citations, process timeline
   ============================================ */

@import './features/messaging/message-bubbles.css';
@import './features/messaging/message-metadata.css';
@import './features/messaging/message-actions.css';
@import './features/composer/input-area.css';
@import './features/composer/quick-prompts.css';
@import './features/composer/actions.css';
@import './features/citations.css';
@import './features/process.css';

/* ============================================
   END OF MAIN STYLESHEET

   MAINTENANCE NOTES:
   - Keep import order strict (core -> themes -> components -> pages -> features)
   - Add new files to appropriate layer section
   - Document any deviations from standard order
   - Phase 1 removes the legacy monolithic imports listed below:
     themes/dark.css
     pages/admin.css
     pages/auth.css
     components/forms.css
     components/sidebar.css
     features/composer.css
     components/buttons.css
     features/messages.css
     components/cards.css

   BUNDLE SIZE TARGET: < 150KB uncompressed
   CRITICAL CSS TARGET: < 14KB (first paint)
   ============================================ */
```

- [ ] **Delete the legacy monolith CSS files**

Run: `Remove-Item 'frontend/src/styles/themes/dark.css', 'frontend/src/styles/pages/admin.css', 'frontend/src/styles/pages/auth.css', 'frontend/src/styles/components/forms.css', 'frontend/src/styles/components/sidebar.css', 'frontend/src/styles/features/composer.css', 'frontend/src/styles/components/buttons.css', 'frontend/src/styles/features/messages.css', 'frontend/src/styles/components/cards.css'`
Expected: The old monolith files are removed and only the split directory structure remains.

- [ ] **Check the new import map**

Run: `rg -n '@import ' frontend/src/styles/main.css`
Expected: The output shows only the new split-file imports and no remaining references to `./themes/dark.css`, `./pages/admin.css`, `./pages/auth.css`, `./components/forms.css`, `./components/sidebar.css`, `./features/composer.css`, `./components/buttons.css`, `./features/messages.css`, or `./components/cards.css`.

- [ ] **Run build verification**

Run (workdir `frontend`): `npm run build`
Expected: `tsc -b && vite build` completes without CSS import resolution, duplicate path, or syntax errors.

- [ ] **Run full smoke validation**

Run (workdir `frontend`): `npm run dev`
Expected: The dev server starts successfully. Then manually verify that the relevant pages have no missing styles, broken layout, dark theme fallback issues, or CSS loading errors in the console.
Expected: Verify `/login`, `/chat`, `/admin`, and `/profile`, and confirm the browser network/CSS sources only show the new split file paths.

- [ ] **Commit**

```bash
git add frontend/src/styles/main.css frontend/src/styles/themes/dark frontend/src/styles/pages/admin frontend/src/styles/pages/auth frontend/src/styles/components/forms frontend/src/styles/components/navigation frontend/src/styles/features/composer frontend/src/styles/components/buttons frontend/src/styles/features/messaging frontend/src/styles/components/cards
git add -u frontend/src/styles
git commit -m "refactor(css): switch main stylesheet to split phase1 modules"
```

## Final Verification Matrix

- [ ] `frontend`: `npm run build` passes without CSS import resolution errors.
- [ ] `/login`: layout, inputs, social login buttons, helper text, and dark mode still match the pre-split behavior.
- [ ] `/chat`: sidebar, message bubbles, composer, quick prompts, and empty state all still render correctly.
- [ ] `/admin`: topbar, tabs, KPI cards, user management table, and audit table still render correctly.
- [ ] `/profile`: no unintended regressions appear from the `main.css` import order change.
- [ ] Browser console and network panel show no 404 CSS requests and no `Failed to resolve import` errors.

## Rollback Notes

- If any split task fails, roll back to the commit immediately before that task.
- If regressions appear only after the import switch, revert Task 10 first and then inspect the relevant split task in isolation.

