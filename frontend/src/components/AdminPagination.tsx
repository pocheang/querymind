import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

type AdminPaginationProps = {
  totalItems: number;
  currentPage: number;
  pageSize: number;
  pageSizeOptions: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
};

const MAX_VISIBLE_PAGES = 7;

export function AdminPagination({
  totalItems,
  currentPage,
  pageSize,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
}: Readonly<AdminPaginationProps>) {
  const { t } = useTranslation();

  // Guard against invalid props
  const safePageSize = pageSize > 0 ? pageSize : pageSizeOptions[0] || 10;
  const safeTotalPages = Math.max(1, Math.ceil(totalItems / safePageSize) || 1);
  const safeCurrentPage = Math.max(1, Math.min(currentPage, safeTotalPages));

  return (
    <nav
      aria-label={t("admin.ui.pagination", "Pagination")}
      className="flex flex-wrap items-center justify-between gap-2 border-t border-line-subtle pt-2.5 text-xs sm:text-sm"
    >
      <span className="font-medium text-ink/80">{t("admin.ui.totalItems", { count: totalItems })}</span>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-1.5 font-medium text-ink/80">
          <span>{t("admin.ui.showPerPage")}</span>
          <select
            value={safePageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value) || pageSizeOptions[0])}
            aria-label={t("admin.ui.itemsPerPage", "Items per page")}
            className="h-7 rounded-control border border-brand-border bg-surface px-2 text-xs text-ink focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <span>{t("admin.ui.items")}</span>
        </label>

        <div className="flex items-center gap-0.5">
          <Button
            variant="secondary"
            size="xs"
            disabled={safeCurrentPage === 1}
            aria-disabled={safeCurrentPage === 1}
            aria-label={t("common.previous") || "Previous page"}
            onClick={() => onPageChange(Math.max(1, safeCurrentPage - 1))}
          >
            {t("common.previous")}
          </Button>

          {Array.from({ length: safeTotalPages }).map((_, idx) => {
            const pageNum = idx + 1;
            if (safeTotalPages > MAX_VISIBLE_PAGES) {
              const isNearCurrent = Math.abs(pageNum - safeCurrentPage) <= 1;
              const isFirstOrLast = pageNum === 1 || pageNum === safeTotalPages;
              if (!isNearCurrent && !isFirstOrLast) {
                if (pageNum === 2 || pageNum === safeTotalPages - 1) {
                  return (
                    /* `--text-faint` is placeholder-only -- it measures 2.52
                       here, and `aria-hidden` hides this from a screen reader,
                       not from a sighted reader. */
                    <span key={pageNum} className="px-1 text-ink-muted" aria-hidden="true">
                      ...
                    </span>
                  );
                }
                return null;
              }
            }
            const current = safeCurrentPage === pageNum;
            return (
              <Button
                key={pageNum}
                variant={current ? "flat" : "ghost"}
                size="xs"
                className="min-w-6 font-mono"
                onClick={() => onPageChange(pageNum)}
                aria-label={t("admin.ui.goToPage", { page: pageNum }) || `Go to page ${pageNum}`}
                aria-current={current ? "page" : undefined}
              >
                {pageNum}
              </Button>
            );
          })}

          <Button
            variant="secondary"
            size="xs"
            disabled={safeCurrentPage === safeTotalPages}
            aria-disabled={safeCurrentPage === safeTotalPages}
            aria-label={t("common.next") || "Next page"}
            onClick={() => onPageChange(Math.min(safeTotalPages, safeCurrentPage + 1))}
          >
            {t("common.next")}
          </Button>
        </div>
      </div>
    </nav>
  );
}
