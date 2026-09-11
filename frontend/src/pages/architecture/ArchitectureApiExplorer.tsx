import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Code, Copy, Eye, Search, Server } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getMethodBadgeClass, parseEndpoints } from "./types";

export function ArchitectureApiExplorer() {
  const { t } = useTranslation();
  const [apiSearch, setApiSearch] = useState("");
  const [selectedApiCategory, setSelectedApiCategory] = useState("all");
  const [copiedPath, setCopiedPath] = useState<string | null>(null);
  const [rawEndpointsView, setRawEndpointsView] = useState(false);

  const rawEndpointsText = useTranslation().t("architecture.apiEndpoints", {
    returnObjects: false,
    interpolation: { escapeValue: false },
  });

  const parsedEndpoints = useMemo(() => parseEndpoints(rawEndpointsText), [rawEndpointsText]);

  const apiCategories = useMemo(() => {
    const set = new Set<string>();
    parsedEndpoints.forEach((item) => set.add(item.category));
    return Array.from(set);
  }, [parsedEndpoints]);

  const filteredEndpoints = useMemo(() => {
    const q = apiSearch.trim().toLowerCase();
    return parsedEndpoints.filter((item) => {
      const matchCategory = selectedApiCategory === "all" || item.category === selectedApiCategory;
      if (!matchCategory) return false;
      if (!q) return true;
      return (
        item.path.toLowerCase().includes(q) ||
        item.method.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
      );
    });
  }, [parsedEndpoints, apiSearch, selectedApiCategory]);

  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(path);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  return (
    <Card className="border-line shadow-elev-1 transition-all">
      <CardHeader className="border-b border-line bg-surface-muted/50 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-control bg-brand-surface text-brand-text border border-brand-border">
              <Server className="size-4.5" aria-hidden="true" />
            </div>
            <div>
              <CardTitle className="text-base sm:text-lg font-bold text-ink">
                {t("architecture.sections.keyEndpoints")}
              </CardTitle>
              <CardDescription className="text-sm text-ink-muted">
                {t("architecture.api.totalEndpoints", { count: parsedEndpoints.length })}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRawEndpointsView((prev) => !prev)}
              className="gap-1.5 text-xs font-medium"
            >
              {rawEndpointsView ? (
                <>
                  <Eye className="size-3.5" />
                  Interactive View
                </>
              ) : (
                <>
                  <Code className="size-3.5" />
                  Raw Reference
                </>
              )}
            </Button>
          </div>
        </div>

        {!rawEndpointsView && (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <div className="relative min-w-[260px] flex-1">
              <Search className="absolute left-3 top-2.5 size-4 text-ink-muted" aria-hidden="true" />
              <Input
                type="text"
                placeholder={t("architecture.api.searchPlaceholder")}
                value={apiSearch}
                onChange={(e) => setApiSearch(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Button
                variant={selectedApiCategory === "all" ? "flat" : "outline"}
                size="xs"
                onClick={() => setSelectedApiCategory("all")}
                className="text-xs py-1.5 px-3"
              >
                {t("architecture.api.allCategories")} ({parsedEndpoints.length})
              </Button>
              {apiCategories.map((cat) => {
                const count = parsedEndpoints.filter((p) => p.category === cat).length;
                return (
                  <Button
                    key={cat}
                    variant={selectedApiCategory === cat ? "flat" : "ghost"}
                    size="xs"
                    onClick={() => setSelectedApiCategory(cat)}
                    className="text-xs py-1.5 px-3"
                  >
                    {cat} ({count})
                  </Button>
                );
              })}
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-5">
        {rawEndpointsView ? (
          <pre className="max-h-[600px] overflow-x-auto rounded-control border border-line bg-surface-muted p-4 font-mono text-xs leading-relaxed text-ink select-text">
            {rawEndpointsText}
          </pre>
        ) : (
          <div className="space-y-2">
            {filteredEndpoints.length === 0 ? (
              <div className="rounded-control border border-dashed border-line p-8 text-center text-sm text-ink-muted">
                No matching API endpoints found for &ldquo;{apiSearch}&rdquo;.
              </div>
            ) : (
              <div className="divide-y divide-line/60 rounded-control border border-line overflow-hidden bg-surface">
                {filteredEndpoints.map((ep) => (
                  <div
                    key={ep.id}
                    className="group flex flex-wrap items-center justify-between gap-3 p-3 text-sm transition-colors hover:bg-surface-muted/50"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className={`inline-flex w-16 shrink-0 justify-center rounded border px-1.5 py-0.5 font-mono text-xs font-bold ${getMethodBadgeClass(
                          ep.method
                        )}`}
                      >
                        {ep.method}
                      </span>
                      <span className="font-mono text-sm font-semibold text-ink select-all">{ep.path}</span>
                      {ep.description && (
                        <span className="hidden text-sm text-ink-muted md:inline-block">
                          • {ep.description}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="neutral" size="xs" className="hidden sm:inline-flex text-xs py-0.5 px-2">
                        {ep.category}
                      </Badge>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleCopyPath(ep.path)}
                        title={t("architecture.api.copy")}
                        className="text-ink-muted hover:text-brand-text"
                      >
                        {copiedPath === ep.path ? (
                          <Check className="size-3.5 text-success" />
                        ) : (
                          <Copy className="size-3.5" />
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
