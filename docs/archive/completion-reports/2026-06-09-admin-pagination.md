# Admin Console Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reusable AdminPagination component and add pagination controls above all Admin Console tables (User Management, Audit Logs, System Logs) with consistent styling.

**Architecture:** Extract pagination UI from AdminUserManagement into a standalone component, add CSS styles matching the Admin Console design system, then integrate into all three table views with appropriate page size options (10/20/50 for users, 20/50/100 for logs).

**Tech Stack:** React, TypeScript, react-i18next, existing Admin Console CSS variables

---

## File Structure

**New Files:**
- `frontend/src/components/AdminPagination.tsx` - Reusable pagination component with page navigation logic

**Modified Files:**
- `frontend/src/styles/pages/admin/tables.css` - Add pagination CSS classes
- `frontend/src/pages/admin/AdminUserManagement.tsx` - Replace inline pagination with component, move to top
- `frontend/src/pages/admin/AdminAuditLogManagement.tsx` - Add pagination state and integrate component
- `frontend/src/pages/AdminPage.tsx` - Add pagination state for audit and system logs

---

## Task 1: Add Pagination CSS Styles

**Files:**
- Modify: `frontend/src/styles/pages/admin/tables.css` (append to end)

- [ ] **Step 1: Add pagination styles to tables.css**

Add the following CSS at the end of the file:

```css
/* ============================================
   Admin Pagination Controls
   ============================================ */

.admin-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--admin-border-medium);
  background: var(--admin-surface);
  margin-bottom: 12px;
}

.admin-pagination-info {
  font-size: 13px;
  color: var(--admin-text-secondary);
  font-weight: 600;
}

.admin-pagination-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.admin-pagination-select-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--admin-text-secondary);
}

.admin-pagination-select-wrap select {
  height: 32px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid var(--admin-input-border);
  background: var(--admin-input-bg);
  color: var(--admin-text-primary);
  font-family: ui-monospace, monospace;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.admin-pagination-select-wrap select:hover {
  border-color: var(--admin-info);
}

.admin-pagination-select-wrap select:focus {
  outline: none;
  border-color: var(--admin-info);
  box-shadow: 0 0 8px var(--admin-info-glow);
}

.admin-pagination-pages {
  display: flex;
  align-items: center;
  gap: 4px;
}

.admin-pagination-btn {
  height: 32px;
  min-width: 32px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid var(--admin-border-medium);
  background: var(--admin-surface);
  color: var(--admin-text-primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.admin-pagination-btn:hover:not(:disabled) {
  border-color: var(--admin-info);
  background: var(--admin-surface-hover);
  color: var(--admin-info);
}

.admin-pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.admin-pagination-btn.active {
  border-color: var(--admin-info);
  background: var(--admin-info);
  color: #fff;
  box-shadow: 0 0 12px var(--admin-info-glow);
}
```

- [ ] **Step 2: Verify CSS file syntax**

Run: `cd frontend && npm run build`

Expected: Build completes without CSS syntax errors

- [ ] **Step 3: Commit CSS changes**

```bash
git add frontend/src/styles/pages/admin/tables.css
git commit -m "style: add admin pagination CSS classes"
```

---

## Task 2: Create AdminPagination Component

**Files:**
- Create: `frontend/src/components/AdminPagination.tsx`

- [ ] **Step 1: Create AdminPagination component file**

```tsx
import { useTranslation } from "react-i18next";

type AdminPaginationProps = {
  totalItems: number;
  currentPage: number;
  pageSize: number;
  pageSizeOptions: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
};

export function AdminPagination({
  totalItems,
  currentPage,
  pageSize,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
}: AdminPaginationProps) {
  const { t } = useTranslation();
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  return (
    <div className="admin-pagination">
      <div className="admin-pagination-info">
        {t("admin.ui.totalItems", { count: totalItems })}
      </div>
      <div className="admin-pagination-controls">
        <div className="admin-pagination-select-wrap">
          <span>{t("admin.ui.showPerPage")}</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value) || pageSizeOptions[0])}
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <span>{t("admin.ui.items")}</span>
        </div>
        <div className="admin-pagination-pages">
          <button
            type="button"
            className="admin-pagination-btn"
            disabled={currentPage === 1}
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          >
            {t("common.previous")}
          </button>
          {Array.from({ length: totalPages }).map((_, idx) => {
            const pageNum = idx + 1;
            if (totalPages > 7) {
              const isNearCurrent = Math.abs(pageNum - currentPage) <= 1;
              const isFirstOrLast = pageNum === 1 || pageNum === totalPages;
              if (!isNearCurrent && !isFirstOrLast) {
                if (pageNum === 2 || pageNum === totalPages - 1) {
                  return (
                    <span key={pageNum} style={{ padding: "0 4px", opacity: 0.5 }}>
                      ...
                    </span>
                  );
                }
                return null;
              }
            }
            return (
              <button
                key={pageNum}
                type="button"
                className={`admin-pagination-btn ${currentPage === pageNum ? "active" : ""}`}
                onClick={() => onPageChange(pageNum)}
              >
                {pageNum}
              </button>
            );
          })}
          <button
            type="button"
            className="admin-pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
          >
            {t("common.next")}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify component builds without errors**

Run: `cd frontend && npm run build`

Expected: Build completes successfully, no TypeScript errors

- [ ] **Step 3: Commit component**

```bash
git add frontend/src/components/AdminPagination.tsx
git commit -m "feat: create AdminPagination reusable component"
```

---

## Task 3: Refactor AdminUserManagement to Use AdminPagination

**Files:**
- Modify: `frontend/src/pages/admin/AdminUserManagement.tsx`

- [ ] **Step 1: Add import for AdminPagination**

At the top of the file, add after existing imports:

```tsx
import { AdminPagination } from "@/components/AdminPagination";
```

- [ ] **Step 2: Move pagination above table**

Find the section around line 166-179 (after the classification editor, before `{loadingUsers && ...}`).

Replace:
```tsx
{loadingUsers && <div className="skeleton-list" />}
{!loadingUsers && (
  <>
    <div className="user-table-wrap">
      <AdminUserTable
```

With:
```tsx
{loadingUsers && <div className="skeleton-list" />}
{!loadingUsers && (
  <>
    {filteredUsers.length > 0 && (
      <AdminPagination
        totalItems={filteredUsers.length}
        currentPage={currentPage}
        pageSize={pageSize}
        pageSizeOptions={[10, 20, 50]}
        onPageChange={setCurrentPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setCurrentPage(1);
        }}
      />
    )}
    <div className="user-table-wrap">
      <AdminUserTable
```

- [ ] **Step 3: Delete old pagination code**

Delete lines 181-249 (the entire old pagination block that starts with `{filteredUsers.length > 0 && (` and contains `<div className="admin-pagination">`).

The section should now end with:
```tsx
        />
      </div>
    </>
  )}
</main>
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`

Expected: Build completes successfully

- [ ] **Step 5: Commit changes**

```bash
git add frontend/src/pages/admin/AdminUserManagement.tsx
git commit -m "refactor: use AdminPagination component in UserManagement, move to top"
```

---

## Task 4: Add Pagination to AdminAuditLogManagement

**Files:**
- Modify: `frontend/src/pages/admin/AdminAuditLogManagement.tsx`
- Modify: `frontend/src/pages/AdminPage.tsx`

- [ ] **Step 1: Add import to AdminAuditLogManagement**

At the top of `frontend/src/pages/admin/AdminAuditLogManagement.tsx`, add:

```tsx
import { AdminPagination } from "@/components/AdminPagination";
```

- [ ] **Step 2: Add pagination props to AdminAuditLogManagement Props type**

In the `Props` type (line 25-44), add:

```tsx
type Props = {
  logs: AuditLogEntry[];
  users: AdminUserSummary[];
  loadingLogs: boolean;
  auditLimit: number;
  auditActorUserId: string;
  auditActionKeyword: string;
  auditEventCategory: string;
  auditSeverity: string;
  auditResult: string;
  auditCurrentPage: number;
  auditPageSize: number;
  formatAuditTime: (ts?: string | null) => string;
  onAuditLimitChange: (value: number) => void;
  onAuditActorUserIdChange: (value: string) => void;
  onAuditActionKeywordChange: (value: string) => void;
  onAuditEventCategoryChange: (value: string) => void;
  onAuditSeverityChange: (value: string) => void;
  onAuditResultChange: (value: string) => void;
  onAuditPageChange: (page: number) => void;
  onAuditPageSizeChange: (size: number) => void;
  onRefresh: () => void;
  onClearFilters: () => void;
};
```

- [ ] **Step 3: Add pagination props to component destructuring**

Update the function signature (line 46-65):

```tsx
export function AdminAuditLogManagement({
  logs,
  users,
  loadingLogs,
  auditLimit,
  auditActorUserId,
  auditActionKeyword,
  auditEventCategory,
  auditSeverity,
  auditResult,
  auditCurrentPage,
  auditPageSize,
  formatAuditTime,
  onAuditLimitChange,
  onAuditActorUserIdChange,
  onAuditActionKeywordChange,
  onAuditEventCategoryChange,
  onAuditSeverityChange,
  onAuditResultChange,
  onAuditPageChange,
  onAuditPageSizeChange,
  onRefresh,
  onClearFilters,
}: Props) {
```

- [ ] **Step 4: Add pagination logic**

After the `hasExactActorMatch` calculation (line 66-73), add:

```tsx
  const paginatedLogs = useMemo(() => {
    const startIdx = (auditCurrentPage - 1) * auditPageSize;
    return logs.slice(startIdx, startIdx + auditPageSize);
  }, [logs, auditCurrentPage, auditPageSize]);
```

Remember to import `useMemo`:
```tsx
import { useMemo } from "react";
```

- [ ] **Step 5: Add AdminPagination component above table**

Find the section around line 159-162. Replace:

```tsx
{loadingLogs && <div className="skeleton-list" />}
{!loadingLogs && <p className="muted admin-audit-scroll-hint">{t("admin.ui.auditScrollHint")}</p>}
{!loadingLogs && logs.length === 0 && <div className="status">{t("admin.ui.auditEmpty")}</div>}
{!loadingLogs && logs.length > 0 && <AdminAuditLogTable logs={logs} formatAuditTime={formatAuditTime} />}
```

With:

```tsx
{loadingLogs && <div className="skeleton-list" />}
{!loadingLogs && <p className="muted admin-audit-scroll-hint">{t("admin.ui.auditScrollHint")}</p>}
{!loadingLogs && logs.length === 0 && <div className="status">{t("admin.ui.auditEmpty")}</div>}
{!loadingLogs && logs.length > 0 && (
  <>
    <AdminPagination
      totalItems={logs.length}
      currentPage={auditCurrentPage}
      pageSize={auditPageSize}
      pageSizeOptions={[20, 50, 100]}
      onPageChange={onAuditPageChange}
      onPageSizeChange={onAuditPageSizeChange}
    />
    <AdminAuditLogTable logs={paginatedLogs} formatAuditTime={formatAuditTime} />
  </>
)}
```

- [ ] **Step 6: Add pagination state and handlers to AdminPage.tsx**

In `frontend/src/pages/AdminPage.tsx`, find where `useAdminState()` is called (line 32). After that, add pagination state:

```tsx
const [auditCurrentPage, setAuditCurrentPage] = useState(1);
const [auditPageSize, setAuditPageSize] = useState(20);
```

Import useState at the top:
```tsx
import { useEffect, useMemo, useState } from "react";
```

- [ ] **Step 7: Add pagination reset effect in AdminPage.tsx**

After the existing useEffect hooks, add:

```tsx
useEffect(() => {
  setAuditCurrentPage(1);
}, [state.auditActorUserId, state.auditActionKeyword, state.auditEventCategory, state.auditSeverity, state.auditResult]);
```

- [ ] **Step 8: Pass pagination props to AdminAuditLogManagement**

Find where `<AdminAuditLogManagement` is rendered in AdminPage.tsx and add the pagination props:

```tsx
<AdminAuditLogManagement
  logs={state.logs}
  users={state.users}
  loadingLogs={state.loadingLogs}
  auditLimit={state.auditLimit}
  auditActorUserId={state.auditActorUserId}
  auditActionKeyword={state.auditActionKeyword}
  auditEventCategory={state.auditEventCategory}
  auditSeverity={state.auditSeverity}
  auditResult={state.auditResult}
  auditCurrentPage={auditCurrentPage}
  auditPageSize={auditPageSize}
  formatAuditTime={formatAuditTime}
  onAuditLimitChange={state.setAuditLimit}
  onAuditActorUserIdChange={state.setAuditActorUserId}
  onAuditActionKeywordChange={state.setAuditActionKeyword}
  onAuditEventCategoryChange={state.setAuditEventCategory}
  onAuditSeverityChange={state.setAuditSeverity}
  onAuditResultChange={state.setAuditResult}
  onAuditPageChange={setAuditCurrentPage}
  onAuditPageSizeChange={(size) => {
    setAuditPageSize(size);
    setAuditCurrentPage(1);
  }}
  onRefresh={actions.loadLogs}
  onClearFilters={() => {
    state.setAuditActorUserId("");
    state.setAuditActionKeyword("");
    state.setAuditEventCategory("");
    state.setAuditSeverity("");
    state.setAuditResult("");
  }}
/>
```

- [ ] **Step 9: Verify build**

Run: `cd frontend && npm run build`

Expected: Build completes successfully

- [ ] **Step 10: Commit changes**

```bash
git add frontend/src/pages/admin/AdminAuditLogManagement.tsx frontend/src/pages/AdminPage.tsx
git commit -m "feat: add pagination to AdminAuditLogManagement"
```

---

## Task 5: Add Pagination to AdminSystemLogTable

**Files:**
- Modify: `frontend/src/pages/admin/AdminSystemLogTable.tsx`
- Modify: `frontend/src/pages/AdminPage.tsx`

- [ ] **Step 1: Add import to AdminSystemLogTable**

At the top of `frontend/src/pages/admin/AdminSystemLogTable.tsx`, add:

```tsx
import { AdminPagination } from "@/components/AdminPagination";
```

- [ ] **Step 2: Add pagination props to AdminSystemLogTable Props type**

In the `Props` type (line 14-28), add:

```tsx
type Props = {
  systemLogs: SystemLog[];
  loadingSystemLogs: boolean;
  systemLogLimit: number;
  systemLogLevel: string;
  systemLogLogger: string;
  systemLogKeyword: string;
  systemLogCurrentPage: number;
  systemLogPageSize: number;
  formatAuditTime: (ts?: string | null) => string;
  onSystemLogLimitChange: (value: number) => void;
  onSystemLogLevelChange: (value: string) => void;
  onSystemLogLoggerChange: (value: string) => void;
  onSystemLogKeywordChange: (value: string) => void;
  onSystemLogPageChange: (page: number) => void;
  onSystemLogPageSizeChange: (size: number) => void;
  onRefresh: () => void;
  onClearFilters: () => void;
};
```

- [ ] **Step 3: Add pagination props to component destructuring**

Update the function signature (line 30-44):

```tsx
export function AdminSystemLogTable({
  systemLogs,
  loadingSystemLogs,
  systemLogLimit,
  systemLogLevel,
  systemLogLogger,
  systemLogKeyword,
  systemLogCurrentPage,
  systemLogPageSize,
  formatAuditTime,
  onSystemLogLimitChange,
  onSystemLogLevelChange,
  onSystemLogLoggerChange,
  onSystemLogKeywordChange,
  onSystemLogPageChange,
  onSystemLogPageSizeChange,
  onRefresh,
  onClearFilters,
}: Props) {
```

- [ ] **Step 4: Add pagination logic**

After the `useTranslation` hook (line 45), add:

```tsx
  const paginatedSystemLogs = useMemo(() => {
    const startIdx = (systemLogCurrentPage - 1) * systemLogPageSize;
    return systemLogs.slice(startIdx, startIdx + systemLogPageSize);
  }, [systemLogs, systemLogCurrentPage, systemLogPageSize]);
```

Import `useMemo`:
```tsx
import { useMemo } from "react";
```

- [ ] **Step 5: Add AdminPagination component above table**

Find the section around line 94-129. Replace:

```tsx
{loadingSystemLogs && <div className="skeleton-list" />}
{!loadingSystemLogs && systemLogs.length === 0 && <div className="status">{t("admin.ui.systemLogEmpty")}</div>}
{!loadingSystemLogs && systemLogs.length > 0 && (
  <div className="audit-table-wrap">
    <table className="table admin-audit-table">
```

With:

```tsx
{loadingSystemLogs && <div className="skeleton-list" />}
{!loadingSystemLogs && systemLogs.length === 0 && <div className="status">{t("admin.ui.systemLogEmpty")}</div>}
{!loadingSystemLogs && systemLogs.length > 0 && (
  <>
    <AdminPagination
      totalItems={systemLogs.length}
      currentPage={systemLogCurrentPage}
      pageSize={systemLogPageSize}
      pageSizeOptions={[20, 50, 100]}
      onPageChange={onSystemLogPageChange}
      onPageSizeChange={onSystemLogPageSizeChange}
    />
    <div className="audit-table-wrap">
      <table className="table admin-audit-table">
```

- [ ] **Step 6: Update table to use paginatedSystemLogs**

Find the `.map` call in the table body (around line 110). Replace:

```tsx
{systemLogs.map((x, idx) => (
```

With:

```tsx
{paginatedSystemLogs.map((x, idx) => (
```

- [ ] **Step 7: Close the new fragment**

At the end of the table section (after `</table>` and `</div>`), add:

```tsx
      </table>
    </div>
  </div>
</>
```

Make sure the structure is:
```tsx
<>
  <AdminPagination ... />
  <div className="audit-table-wrap">
    <table>...</table>
  </div>
</>
```

- [ ] **Step 8: Add pagination state to AdminPage.tsx**

In `frontend/src/pages/AdminPage.tsx`, after the audit pagination state, add:

```tsx
const [systemLogCurrentPage, setSystemLogCurrentPage] = useState(1);
const [systemLogPageSize, setSystemLogPageSize] = useState(20);
```

- [ ] **Step 9: Add pagination reset effect in AdminPage.tsx**

After the audit pagination reset effect, add:

```tsx
useEffect(() => {
  setSystemLogCurrentPage(1);
}, [state.systemLogLevel, state.systemLogLogger, state.systemLogKeyword]);
```

- [ ] **Step 10: Pass pagination props to AdminSystemLogTable**

Find where `<AdminSystemLogTable` is rendered in AdminPage.tsx and add pagination props:

```tsx
<AdminSystemLogTable
  systemLogs={state.systemLogs}
  loadingSystemLogs={state.loadingSystemLogs}
  systemLogLimit={state.systemLogLimit}
  systemLogLevel={state.systemLogLevel}
  systemLogLogger={state.systemLogLogger}
  systemLogKeyword={state.systemLogKeyword}
  systemLogCurrentPage={systemLogCurrentPage}
  systemLogPageSize={systemLogPageSize}
  formatAuditTime={formatAuditTime}
  onSystemLogLimitChange={state.setSystemLogLimit}
  onSystemLogLevelChange={state.setSystemLogLevel}
  onSystemLogLoggerChange={state.setSystemLogLogger}
  onSystemLogKeywordChange={state.setSystemLogKeyword}
  onSystemLogPageChange={setSystemLogCurrentPage}
  onSystemLogPageSizeChange={(size) => {
    setSystemLogPageSize(size);
    setSystemLogCurrentPage(1);
  }}
  onRefresh={actions.loadSystemLogs}
  onClearFilters={() => {
    state.setSystemLogLevel("");
    state.setSystemLogLogger("");
    state.setSystemLogKeyword("");
  }}
/>
```

- [ ] **Step 11: Verify build**

Run: `cd frontend && npm run build`

Expected: Build completes successfully

- [ ] **Step 12: Commit changes**

```bash
git add frontend/src/pages/admin/AdminSystemLogTable.tsx frontend/src/pages/AdminPage.tsx
git commit -m "feat: add pagination to AdminSystemLogTable"
```

---

## Task 6: Manual Testing

**Files:**
- Test: All modified components in browser

- [ ] **Step 1: Start development server**

Run: `cd frontend && npm run dev`

Expected: Dev server starts on http://localhost:5173

- [ ] **Step 2: Test User Management pagination**

1. Navigate to Admin Console → Users
2. Verify pagination appears ABOVE the table
3. Verify "Total X items" displays correctly
4. Verify page size selector has options: 10, 20, 50
5. Change page size to 20, verify table updates and resets to page 1
6. Click page 2, verify table shows next 20 users
7. Click Previous/Next buttons, verify navigation works
8. Apply a filter, verify pagination resets to page 1
9. Verify active page button is highlighted
10. Verify Previous is disabled on page 1, Next is disabled on last page

Expected: All behaviors work correctly

- [ ] **Step 3: Test Audit Log pagination**

1. Navigate to Admin Console → Audit Logs
2. Verify pagination appears ABOVE the table
3. Verify "Total X items" displays correctly (in Chinese if language is set to Chinese)
4. Verify page size selector has options: 20, 50, 100
5. Change page size to 50, verify table updates
6. Navigate through pages, verify pagination works
7. Apply a filter, verify pagination resets to page 1
8. Verify "最近 100/200/500" selector still works for server-side limiting

Expected: All behaviors work correctly

- [ ] **Step 4: Test System Log pagination**

1. Navigate to Admin Console → System Logs
2. Verify pagination appears ABOVE the table
3. Verify page size selector has options: 20, 50, 100
4. Test page navigation
5. Apply filters, verify pagination resets
6. Verify "最近 100/200/500" selector still works

Expected: All behaviors work correctly

- [ ] **Step 5: Test pagination with >7 pages**

1. Set User Management page size to 10
2. If you have > 70 users, verify ellipsis appears correctly
3. Verify pattern: `1 ... 4 5 6 ... 10` when on page 5
4. Verify first and last pages always show

Expected: Smart ellipsis works correctly

- [ ] **Step 6: Test translations**

1. Switch language to English, verify all pagination text is in English
2. Switch language to Chinese, verify all pagination text is in Chinese
3. Verify "Total X items" / "共 X 条记录" renders correctly
4. Verify "Show ... items" / "每页显示 ... 条" renders correctly

Expected: Both languages work correctly

- [ ] **Step 7: Verify styling consistency**

1. Check all three tables have identical pagination styling
2. Verify hover effects on buttons
3. Verify active button highlighting
4. Verify disabled button styling
5. Verify select dropdown styling matches other Admin Console dropdowns

Expected: Styling is consistent across all tables and matches Admin Console design

- [ ] **Step 8: Document test results**

Create a brief test report noting any issues found.

Expected: No major issues, all success criteria met

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Create AdminPagination component (Task 2)
- ✅ Add CSS styles (Task 1)
- ✅ Move User Management pagination to top (Task 3)
- ✅ Add pagination to Audit Logs (Task 4)
- ✅ Add pagination to System Logs (Task 5)
- ✅ User Management: 10/20/50 options (Task 3, Step 2)
- ✅ Logs: 20/50/100 options (Task 4 Step 5, Task 5 Step 5)
- ✅ Translations (existing keys, verified in Task 6)
- ✅ Manual testing (Task 6)

**Placeholder scan:**
- ✅ No TBD, TODO, or "implement later" statements
- ✅ All code blocks are complete
- ✅ All commands have expected outputs
- ✅ All file paths are exact

**Type consistency:**
- ✅ Props types match across all components
- ✅ Function names consistent (onPageChange, onPageSizeChange)
- ✅ State variable names consistent (auditCurrentPage, systemLogCurrentPage)
- ✅ CSS class names match between styles and JSX

---

## Success Criteria

- ✅ Pagination controls appear above all three tables
- ✅ Visual style is consistent across all tables
- ✅ User Management: 10/20/50 options
- ✅ Audit & System Logs: 20/50/100 options
- ✅ All translations work in English and Chinese
- ✅ Page navigation works smoothly
- ✅ Filter changes reset to page 1
- ✅ Design matches Admin Console aesthetic
