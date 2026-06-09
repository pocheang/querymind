# Admin Console Pagination Design

**Date:** 2026-06-09  
**Status:** Approved  
**Author:** Claude Code

## Overview

Unify pagination controls across all Admin Console tables by creating a reusable `AdminPagination` component and placing pagination controls above tables for better UX consistency.

## Requirements

### Scope
- Add pagination to **Audit Log** and **System Log** tables
- Move **User Management** pagination from below table to above table
- Ensure consistent styling across all three tables
- Support different page size options per table type

### User Requirements
- **Total items display**: Show "Total X items" / "共 X 条记录"
- **Page size selector**: Dropdown to select items per page
- **Page navigation**: Previous/Next buttons + numbered page buttons
- **Visual consistency**: Match existing Admin Console design system

## Architecture

### Component Structure

```
AdminPagination (new component)
├── Props
│   ├── totalItems: number
│   ├── currentPage: number
│   ├── pageSize: number
│   ├── pageSizeOptions: number[]
│   ├── onPageChange: (page: number) => void
│   └── onPageSizeChange: (size: number) => void
├── Layout
│   ├── Left: Total items info
│   └── Right: Page size selector + Page buttons
```

### File Structure

**New Files:**
- `frontend/src/components/AdminPagination.tsx` - Reusable pagination component

**Modified Files:**
- `frontend/src/pages/admin/AdminUserManagement.tsx` - Replace inline pagination with component, move to top
- `frontend/src/pages/admin/AdminAuditLogManagement.tsx` - Add pagination state and component
- `frontend/src/pages/admin/AdminSystemLogTable.tsx` - Add pagination state and component
- `frontend/src/styles/pages/admin/tables.css` - Add pagination styles

## Design Details

### 1. AdminPagination Component

**Location:** `frontend/src/components/AdminPagination.tsx`

**Props Interface:**
```typescript
type AdminPaginationProps = {
  totalItems: number;           // Total number of items
  currentPage: number;          // Current page (1-indexed)
  pageSize: number;             // Items per page
  pageSizeOptions: number[];    // Available page size options
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
};
```

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Total 123 items    Show [20 ▼] items  [<] 1 2 3 4 5 [>]   │
└─────────────────────────────────────────────────────────────┘
```

**JSX Structure:**
```tsx
<div className="admin-pagination">
  <div className="admin-pagination-info">
    {t("admin.ui.totalItems", { count: totalItems })}
  </div>
  <div className="admin-pagination-controls">
    <div className="admin-pagination-select-wrap">
      <span>{t("admin.ui.showPerPage")}</span>
      <select value={pageSize} onChange={...}>
        {pageSizeOptions.map(option => <option>{option}</option>)}
      </select>
      <span>{t("admin.ui.items")}</span>
    </div>
    <div className="admin-pagination-pages">
      <button disabled={currentPage === 1}>{t("common.previous")}</button>
      {/* Page number buttons with smart ellipsis */}
      <button disabled={currentPage === totalPages}>{t("common.next")}</button>
    </div>
  </div>
</div>
```

**Page Number Logic:**
- Display all page numbers if total pages ≤ 7
- For total pages > 7: Show `1 ... current-1 current current+1 ... last`
- Example: `1 ... 4 5 6 ... 10` (current page = 5, total = 10)
- Ellipsis rendered as `<span style="padding: 0 4px; opacity: 0.5">...</span>`

**Why:** This logic is already proven in AdminUserManagement and provides good UX for large datasets.

### 2. CSS Styling

**Location:** `frontend/src/styles/pages/admin/tables.css`

**Classes:**
```css
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

**Why:** These styles match the existing Admin Console design system (tactical, high-tech aesthetic with glow effects, monospace fonts, and consistent spacing).

### 3. Integration Changes

#### AdminUserManagement

**Changes:**
1. **Import** the new `AdminPagination` component
2. **Move** pagination from below table (line 181-249) to above table
3. **Position**: After filters, before `user-table-wrap`
4. **Delete** existing inline pagination JSX (line 181-249)

**Before:**
```tsx
<div className="user-table-wrap">
  <AdminUserTable ... />
</div>
{/* Pagination here (old location) */}
```

**After:**
```tsx
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
  <AdminUserTable users={paginatedUsers} ... />
</div>
```

**Why:** User Management already has complete pagination logic, we just extract UI and reposition.

#### AdminAuditLogManagement

**Changes:**
1. **Add** pagination state (in parent component that renders AdminAuditLogManagement, likely AdminPage.tsx)
2. **Add** client-side pagination logic
3. **Add** `<AdminPagination>` component above the table
4. **Position**: After filters, before loading/empty states and table
5. **Keep** existing "最近 100/200/500" selector for server-side data limit

**New State:**
```tsx
const [auditCurrentPage, setAuditCurrentPage] = useState(1);
const [auditPageSize, setAuditPageSize] = useState(20);
```

**Pagination Logic:**
```tsx
const paginatedLogs = useMemo(() => {
  const startIdx = (auditCurrentPage - 1) * auditPageSize;
  return logs.slice(startIdx, startIdx + auditPageSize);
}, [logs, auditCurrentPage, auditPageSize]);
```

**UI Position:**
```tsx
{/* Existing filters */}
{loadingLogs && <div className="skeleton-list" />}
{!loadingLogs && <p className="muted admin-audit-scroll-hint">...</p>}
{!loadingLogs && logs.length === 0 && <div className="status">...</div>}
{!loadingLogs && logs.length > 0 && (
  <>
    <AdminPagination
      totalItems={logs.length}
      currentPage={auditCurrentPage}
      pageSize={auditPageSize}
      pageSizeOptions={[20, 50, 100]}
      onPageChange={setAuditCurrentPage}
      onPageSizeChange={(size) => {
        setAuditPageSize(size);
        setAuditCurrentPage(1);
      }}
    />
    <AdminAuditLogTable logs={paginatedLogs} formatAuditTime={formatAuditTime} />
  </>
)}
```

**Why:** 
- Audit logs can be large datasets, so 20/50/100 options are more appropriate
- Keep server-side limit selector as primary data filter, add client-side pagination for viewing
- Two-tier approach: server limits total data fetched, client pagination controls display

#### AdminSystemLogTable

**Changes:**
1. **Add** pagination state props
2. **Add** client-side pagination logic in parent
3. **Add** `<AdminPagination>` component above the table
4. **Position**: After filters, before loading/empty states and table
5. **Keep** existing "最近 100/200/500" selector for server-side data limit

**Component Signature Update:**
```tsx
type Props = {
  // ... existing props
  systemLogCurrentPage: number;
  systemLogPageSize: number;
  onSystemLogPageChange: (page: number) => void;
  onSystemLogPageSizeChange: (size: number) => void;
};
```

**UI Position:**
```tsx
{/* Existing filters */}
{loadingSystemLogs && <div className="skeleton-list" />}
{!loadingSystemLogs && systemLogs.length === 0 && <div className="status">...</div>}
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
        {/* ... existing table */}
      </table>
    </div>
  </>
)}
```

**Parent (AdminPage.tsx) State:**
```tsx
const [systemLogCurrentPage, setSystemLogCurrentPage] = useState(1);
const [systemLogPageSize, setSystemLogPageSize] = useState(20);

const paginatedSystemLogs = useMemo(() => {
  const startIdx = (systemLogCurrentPage - 1) * systemLogPageSize;
  return systemLogs.slice(startIdx, startIdx + systemLogPageSize);
}, [systemLogs, systemLogCurrentPage, systemLogPageSize]);
```

**Why:** Similar reasoning to Audit Logs - large datasets benefit from 20/50/100 options and two-tier filtering.

### 4. Internationalization

**Existing Keys (No Changes Needed):**
- `admin.ui.totalItems`: "Total {{count}} items" / "共 {{count}} 条记录"
- `admin.ui.showPerPage`: "Show" / "每页显示"
- `admin.ui.items`: "items" / "条"
- `common.previous`: "Previous" / "上一页"
- `common.next`: "Next" / "下一页"

All required translation keys already exist in `frontend/src/i18n/locales/en.json` and `zh.json`.

**Why:** Reusing existing translations maintains consistency and avoids duplication.

## Data Flow

### User Management
```
filteredUsers (all) 
  → AdminPagination (controls)
  → paginatedUsers (slice)
  → AdminUserTable (display)
```

### Audit Logs
```
logs (server-limited by auditLimit 100/200/500)
  → AdminPagination (controls)
  → paginatedLogs (slice)
  → AdminAuditLogTable (display)
```

### System Logs
```
systemLogs (server-limited by systemLogLimit 100/200/500)
  → AdminPagination (controls)
  → paginatedSystemLogs (slice)
  → table (display)
```

**Why:** Client-side pagination provides instant navigation without server round-trips. Server-side limits prevent loading excessive data.

## Edge Cases & Behaviors

1. **Empty data**: Pagination should not render when `totalItems === 0`
2. **Filter changes**: Reset to page 1 when filters change (already implemented in UserManagement via useEffect)
3. **Page size change**: Reset to page 1 when page size changes
4. **Current page out of bounds**: If current page > total pages after filtering, reset to page 1
5. **Disabled buttons**: Previous disabled on page 1, Next disabled on last page
6. **Single page**: All page buttons should still render even if only 1 page exists

**Why:** These behaviors match existing UserManagement implementation and provide expected UX.

## Implementation Order

1. **Create AdminPagination component** with all logic and styling
2. **Add CSS styles** to tables.css
3. **Refactor AdminUserManagement** to use new component (test existing functionality preserved)
4. **Add pagination to AdminAuditLogManagement** (requires parent component state updates)
5. **Add pagination to AdminSystemLogTable** (requires parent component state updates)
6. **Test all three tables** for consistency and functionality

**Why:** Starting with the component and testing on existing UserManagement ensures the component works before applying to new areas.

## Testing Checklist

- [ ] AdminPagination component renders correctly with all props
- [ ] Page size selector updates page size and resets to page 1
- [ ] Previous/Next buttons navigate correctly
- [ ] Page number buttons navigate correctly
- [ ] Active page is visually highlighted
- [ ] Disabled states work correctly
- [ ] Ellipsis appears correctly for >7 pages
- [ ] Total count displays correctly
- [ ] User Management pagination moved to top and works
- [ ] Audit Log pagination works with server limit + client pagination
- [ ] System Log pagination works with server limit + client pagination
- [ ] Styles match Admin Console design system
- [ ] Translations work in both English and Chinese
- [ ] Responsive behavior on smaller screens
- [ ] Filter changes reset to page 1

## Open Questions

None - all requirements clarified.

## Success Criteria

1. ✅ Pagination controls appear **above** all three tables
2. ✅ Visual style is consistent across all tables
3. ✅ User Management: 10/20/50 options
4. ✅ Audit & System Logs: 20/50/100 options
5. ✅ All translations work correctly
6. ✅ Page navigation works smoothly
7. ✅ Design matches existing Admin Console aesthetic
