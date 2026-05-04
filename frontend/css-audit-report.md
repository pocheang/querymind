# CSS Audit Report

**Generated:** 5/1/2026, 3:04:19 PM

## 📊 Summary

- **Total CSS Files:** 13
- **Total Size:** 195.60 KB
- **Unused CSS:** 0.00%
- **Duplicate Rules:** 19
- **High Specificity Selectors:** 88
- **!important Usage:** 5

## 📁 File Sizes

| File | Size (KB) | Lines |
|------|-----------|-------|
| chat-workbench.css | 38.47 | 1994 |
| pages.css | 35.60 | 1501 |
| components.css | 28.73 | 1474 |
| modern-ui-enhancements.css | 16.91 | 705 |
| chat-console.css | 14.54 | 726 |
| final-polish.css | 12.28 | 512 |
| ui-polish.css | 11.63 | 582 |
| precision-adjustments.css | 9.89 | 403 |
| base.css | 7.94 | 300 |
| sidebar.css | 6.83 | 391 |
| profile.css | 6.04 | 371 |
| admin.css | 5.37 | 255 |
| tables.css | 1.37 | 70 |

## 🗑️ Unused CSS Analysis

| File | Original Size | Unused % | Rejected Rules |
|------|---------------|----------|----------------|
| admin.css | 5.32 KB | 0.00% | 0 |
| base.css | 6.86 KB | 0.00% | 0 |
| chat-console.css | 14.54 KB | 0.00% | 0 |
| chat-workbench.css | 38.39 KB | 0.00% | 0 |
| components.css | 28.37 KB | 0.00% | 0 |
| final-polish.css | 12.04 KB | 0.00% | 0 |
| modern-ui-enhancements.css | 16.66 KB | 0.00% | 0 |
| pages.css | 35.11 KB | 0.00% | 0 |
| precision-adjustments.css | 9.48 KB | 0.00% | 0 |
| profile.css | 6.04 KB | 0.00% | 0 |
| sidebar.css | 6.83 KB | 0.00% | 0 |
| tables.css | 1.37 KB | 0.00% | 0 |
| ui-polish.css | 11.34 KB | 0.00% | 0 |

## 🔁 Top Duplicate Rules

1. Found in: chat-workbench.css, chat-workbench.css
   `to { opacity: 1; transform: translateY(0); }...`

2. Found in: chat-workbench.css, chat-workbench.css
   `to { opacity: 1; transform: translateY(0); }...`

3. Found in: chat-workbench.css, components.css
   `to { opacity: 1; transform: translateY(0); }...`

4. Found in: chat-workbench.css, components.css
   `0% { transform: translateX(-100%); }...`

5. Found in: chat-workbench.css, components.css
   `100% { transform: translateX(100%); }...`

6. Found in: components.css, components.css
   `from { opacity: 0; transform: translateY(20px); }...`

7. Found in: chat-workbench.css, components.css
   `to { opacity: 1; transform: translateY(0); }...`

8. Found in: chat-workbench.css, final-polish.css
   `.bubble.user .message-role { color: #1e40af; }...`

9. Found in: chat-workbench.css, final-polish.css
   `.bubble.assistant .message-role { color: #667eea; }...`

10. Found in: final-polish.css, modern-ui-enhancements.css
   `.bubble:hover .row-actions { opacity: 1; }...`

11. Found in: chat-workbench.css, modern-ui-enhancements.css
   `.option-agent { margin-left: 0; }...`

12. Found in: chat-workbench.css, pages.css
   `.status.ok { background: var(--success-light); border-color: var(--success); color: var(--success); ...`

13. Found in: modern-ui-enhancements.css, pages.css
   `.compact-list li:last-child { border-bottom: none; }...`

14. Found in: chat-workbench.css, pages.css
   `to { opacity: 1; transform: translateY(0); }...`

15. Found in: final-polish.css, precision-adjustments.css
   `.composer-main textarea::placeholder { color: #94a3b8; opacity: 0.9; }...`

16. Found in: final-polish.css, precision-adjustments.css
   `:root[data-theme="dark"] .option-label { color: #cbd5e1; }...`

17. Found in: chat-workbench.css, precision-adjustments.css
   `.quick-prompt-row { gap: 6px; }...`

18. Found in: precision-adjustments.css, ui-polish.css
   `:root[data-theme="dark"] .composer-main textarea::placeholder { color: #64748b; }...`

19. Found in: pages.css, ui-polish.css
   `:root[data-theme="dark"] .option-label { color: #94a3b8; }...`

## ⚠️ !important Usage

| File | Count |
|------|-------|
| components.css | 4 |
| profile.css | 1 |

## 🎯 High Specificity Selectors (Top 20)

| File | Selector | Specificity |
|------|----------|-------------|
| admin.css | `/* ============================================
   Admin KPI Cards
   ========` | 40 |
| admin.css | `.admin-shell .admin-field input,
.admin-shell .admin-field select,
.admin-shel` | 60 |
| admin.css | `.admin-shell .row-actions button,
.admin-shell .row-actions .link-btn` | 50 |
| admin.css | `.admin-shell .table td,
.admin-shell .table th` | 40 |
| base.css | `html,
body,
#root` | 100 |
| chat-console.css | `.page-shell .sidebar-history,
.page-shell .sidebar-tools` | 40 |
| chat-console.css | `.page-shell .sidebar-module-copy small,
.page-shell .sidebar small.muted,
.page-` | 80 |
| chat-console.css | `.page-shell .sidebar-kb-card,
.page-shell .pdf-kpi-card` | 40 |
| chat-console.css | `.page-shell .sidebar-kb-card span,
.page-shell .pdf-kpi-card span` | 40 |
| chat-console.css | `.page-shell .sidebar-kb-card strong,
.page-shell .pdf-kpi-card strong` | 40 |
| chat-console.css | `.page-shell .sidebar-history-panel .section-head,
.page-shell .sidebar-module-bo` | 70 |
| chat-console.css | `.page-shell .session-item.active .session-main-btn` | 40 |
| chat-console.css | `.page-shell .sidebar input,
.page-shell .sidebar textarea,
.page-shell .sidebar ` | 60 |
| chat-console.css | `.page-shell .upload-box,
.page-shell .dropzone,
.page-shell .doc-row,
.page-shel` | 100 |
| chat-console.css | `.page-shell .upload-box,
.page-shell .prompt-row,
.page-shell .doc-row` | 60 |
| chat-console.css | `.page-shell .topbar-btn,
.page-shell .user-badge` | 40 |
| chat-console.css | `.page-shell .topbar-btn::before,
.page-shell .user-badge::before` | 40 |
| chat-console.css | `.page-shell .topbar-btn:hover,
.page-shell .user-badge.clickable:hover` | 50 |
| chat-console.css | `.page-shell .bubble.assistant::after,
.page-shell .bubble.user::before` | 60 |
| chat-console.css | `.page-shell .bubble.user .message-role` | 40 |

## 💡 Recommendations

1. **Remove unused CSS:** 0.00% of CSS is unused
2. **Deduplicate rules:** 19 duplicate rules found
3. **Reduce !important:** 5 instances found
4. **Lower specificity:** 88 high-specificity selectors

---

**Next Steps:** Proceed to Phase 1 of the CSS refactoring plan.
