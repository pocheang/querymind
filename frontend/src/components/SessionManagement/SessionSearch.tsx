/**
 * SessionSearch Component
 *
 * Advanced session search with text query, tag filters, category filter,
 * time ranges, and query count ranges. Displays paginated results with
 * relevance scores and matched tags highlighting.
 */

import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { sessionManagementApi, SearchQuery, SearchResult, SessionCategory } from "../../services/sessionManagement";
import { TagInput } from "./TagInput";
import { activateOnKey } from "@/lib/a11y";
import { Search, SlidersHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SessionSearchProps {
  onSelectSession?: (sessionId: string) => void;
}

export const SessionSearch: React.FC<SessionSearchProps> = ({ onSelectSession }) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Search query state
  const [searchText, setSearchText] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<SessionCategory | null>(null);
  const [minQueries, setMinQueries] = useState<number | undefined>();
  const [maxQueries, setMaxQueries] = useState<number | undefined>();
  const [sortBy, setSortBy] = useState<"updated_at" | "created_at" | "query_count">("updated_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Results state
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize] = useState(20);

  const categories: SessionCategory[] = ["research", "development", "debugging", "learning", "other"];

  // Search on mount and when filters change
  useEffect(() => {
    handleSearch();
  }, [page, sortBy, sortOrder]);

  const handleSearch = async () => {
    setLoading(true);

    try {
      const query: SearchQuery = {
        q: searchText.trim() || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
        category: selectedCategory || undefined,
        min_queries: minQueries,
        max_queries: maxQueries,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: pageSize,
        offset: page * pageSize,
      };

      const response = await sessionManagementApi.search(query);
      setResults(response.results);
      setTotal(response.total);
    } catch (error) {
      console.error("Search failed:", error);
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchClick = () => {
    setPage(0); // Reset to first page
    handleSearch();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearchClick();
    }
  };

  const handleClearFilters = () => {
    setSearchText("");
    setSelectedTags([]);
    setSelectedCategory(null);
    setMinQueries(undefined);
    setMaxQueries(undefined);
    setPage(0);
  };

  const handleResultClick = (sessionId: string) => {
    if (onSelectSession) {
      onSelectSession(sessionId);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const totalPages = Math.ceil(total / pageSize);

  const SELECT =
    "h-7 rounded-control border border-brand-border bg-surface px-2 text-xs text-ink focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]";

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <h3 className="text-sm font-bold text-ink">{t("sessionManagement.searchSessions")}</h3>

        <div className="flex items-center gap-1.5">
          <label className="field-shell flex flex-1 items-center gap-2 rounded-control border border-brand-border bg-surface px-2.5 py-1.5 transition-all focus-within:border-brand-accent focus-within:ring-2 focus-within:ring-[var(--brand-ring)]">
            <Search className="size-4 shrink-0 text-ink-faint" aria-hidden="true" />
            <input
              type="text"
              className="w-full bg-transparent text-xs sm:text-sm text-ink placeholder:text-ink-faint focus-visible:outline-none"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t("sessionManagement.searchPlaceholder")}
              disabled={loading}
            />
          </label>
          <Button size="sm" onClick={handleSearchClick} disabled={loading}>
            {loading ? t("common.searching") : t("common.search")}
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <Button variant="ghost" size="xs" onClick={() => setShowFilters(!showFilters)}>
          <SlidersHorizontal className="size-3.5" aria-hidden="true" />
          {showFilters ? t("common.hideFilters") : t("common.showFilters")}
        </Button>

        {showFilters && (
          <div className="space-y-2 rounded-card border border-line bg-surface-inset p-2.5">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label>{t("sessionManagement.filterByTags")}</Label>
                <TagInput
                  value={selectedTags}
                  onChange={setSelectedTags}
                  placeholder={t("sessionManagement.selectTags")}
                  maxTags={5}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="filter-category">{t("sessionManagement.filterByCategory")}</Label>
                <select
                  id="filter-category"
                  className={cn(SELECT, "h-8 w-full text-xs")}
                  value={selectedCategory || ""}
                  onChange={(e) => setSelectedCategory((e.target.value || null) as SessionCategory | null)}
                >
                  <option value="">{t("sessionManagement.allCategories")}</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {t(`sessionManagement.categories.${cat}`)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="filter-min">{t("sessionManagement.minQueries")}</Label>
                  <Input
                    id="filter-min"
                    type="number"
                    value={minQueries || ""}
                    onChange={(e) => setMinQueries(e.target.value ? Number.parseInt(e.target.value, 10) : undefined)}
                    min={0}
                    placeholder="0"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="filter-max">{t("sessionManagement.maxQueries")}</Label>
                  <Input
                    id="filter-max"
                    type="number"
                    value={maxQueries || ""}
                    onChange={(e) => setMaxQueries(e.target.value ? Number.parseInt(e.target.value, 10) : undefined)}
                    min={0}
                    placeholder="&#8734;"
                  />
                </div>
              </div>
            </div>

            <div className="text-right">
              <Button variant="ghost" size="xs" onClick={handleClearFilters}>
                {t("common.clearFilters")}
              </Button>
            </div>
          </div>
        )}
      </div>

      {!loading && results.length > 0 && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs sm:text-sm font-semibold text-ink">
              {t("sessionManagement.resultsCount", { count: total })}
            </span>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-ink/80">{t("common.sortBy")}:</span>
              <select className={SELECT} value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
                <option value="updated_at">{t("sessionManagement.sortUpdated")}</option>
                <option value="created_at">{t("sessionManagement.sortCreated")}</option>
                <option value="query_count">{t("sessionManagement.sortQueries")}</option>
              </select>
              <select className={SELECT} value={sortOrder} onChange={(e) => setSortOrder(e.target.value as any)}>
                <option value="desc">{t("common.descending")}</option>
                <option value="asc">{t("common.ascending")}</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            {results.map((result) => (
              <div
                key={result.session_id}
                className="cursor-pointer rounded-card border border-line bg-surface p-3 transition-all hover:border-brand-border-strong hover:bg-brand-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
                role="button"
                tabIndex={0}
                onClick={() => handleResultClick(result.session_id)}
                onKeyDown={activateOnKey(() => handleResultClick(result.session_id))}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-xs sm:text-sm font-semibold text-ink">{result.session_id}</span>
                  <Badge variant="brand" size="xs" mono>
                    {t("sessionManagement.score")}: {result.score.toFixed(2)}
                  </Badge>
                </div>

                {result.metadata.description && (
                  <p className="mt-1 line-clamp-2 text-xs text-ink/80 leading-relaxed">{result.metadata.description}</p>
                )}

                <dl className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink/80">
                  <div className="flex gap-1">
                    <dt className="font-medium">{t("sessionManagement.category")}:</dt>
                    <dd className="text-ink">
                      {result.metadata.category ? t(`sessionManagement.categories.${result.metadata.category}`) : "-"}
                    </dd>
                  </div>
                  <div className="flex gap-1">
                    <dt className="font-medium">{t("sessionManagement.queries")}:</dt>
                    <dd className="font-mono text-ink">{result.metadata.query_count}</dd>
                  </div>
                  <div className="flex gap-1">
                    <dt className="font-medium">{t("common.updated")}:</dt>
                    <dd className="font-mono text-ink">{formatDate(result.metadata.updated_at)}</dd>
                  </div>
                </dl>

                {result.metadata.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {result.metadata.tags.map((tag) => (
                      <Badge key={tag} variant={result.matched_tags?.includes(tag) ? "brand" : "neutral"} size="pill">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between gap-2 border-t border-line-subtle pt-2.5">
              <Button variant="secondary" size="xs" onClick={() => setPage(page - 1)} disabled={page === 0}>
                {t("common.previous")}
              </Button>
              <span className="font-mono text-xs font-medium text-ink/80">
                {t("common.pageOf", { current: page + 1, total: totalPages })}
              </span>
              <Button variant="secondary" size="xs" onClick={() => setPage(page + 1)} disabled={page >= totalPages - 1}>
                {t("common.next")}
              </Button>
            </div>
          )}
        </>
      )}

      {!loading && results.length === 0 && (
        <div className="space-y-2 py-8 text-center">
          <Search className="mx-auto size-7 text-ink-faint" strokeWidth={1.5} aria-hidden="true" />
          <h4 className="text-sm font-semibold text-ink">{t("sessionManagement.noResults")}</h4>
          <p className="text-xs sm:text-sm text-ink/80">
            {t("sessionManagement.searchesMetadataOnly")}
          </p>
        </div>
      )}
    </div>
  );
};
