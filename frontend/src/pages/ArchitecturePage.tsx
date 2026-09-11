import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Activity,
  Check,
  Code,
  Copy,
  Cpu,
  Database,
  Eye,
  FileText,
  Layers,
  Lock,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PipelineFlowDiagram } from "@/components/architecture/PipelineFlowDiagram";
import { LanguageToggle } from "@/components/LanguageToggle";

type Props = {
  isLoggedIn: boolean;
};

type PillarId = "all" | "pipeline" | "retrieval" | "security" | "database" | "operations" | "endpoints";

interface CardSectionConfig {
  key: string;
  titleKey: string;
  pillar: PillarId;
  icon: React.ComponentType<{ className?: string }>;
  tags: string[];
}

interface ParsedEndpoint {
  id: string;
  method: string;
  path: string;
  description: string;
  category: string;
}

const ARCHITECTURE_CARDS: CardSectionConfig[] = [
  {
    key: "pipeline",
    titleKey: "architecture.sections.pipeline",
    pillar: "pipeline",
    icon: Workflow,
    tags: ["LangGraph", "Router (>99%)", "Planner", "ReAct", "Synthesizer", "Finalizer", "SSE Stream"],
  },
  {
    key: "coreMethods",
    titleKey: "architecture.sections.coreMethods",
    pillar: "pipeline",
    icon: Sparkles,
    tags: ["5 QA Validators", "Route Quality", "NLI Hallucination", "LRU Cache", "Self-RAG", "CI/CD Gate"],
  },
  {
    key: "hybridRetrieval",
    titleKey: "architecture.sections.hybridRetrieval",
    pillar: "retrieval",
    icon: Search,
    tags: ["Dense BGE-M3", "Sparse BM25", "RRF Fusion", "BGE-Reranker-V2-M3", "Neo4j Graph", "Tenant Scope"],
  },
  {
    key: "multimodalIngestion",
    titleKey: "architecture.sections.multimodalIngestion",
    pillar: "retrieval",
    icon: FileText,
    tags: ["Streaming PDF (-70%)", "Tesseract OCR", "Chart Extraction", "Parent-Child (1500/600)", "Hot Reindex"],
  },
  {
    key: "groundingSecurity",
    titleKey: "architecture.sections.groundingSecurity",
    pillar: "security",
    icon: ShieldCheck,
    tags: ["Citation-First [1][2]", "Sentence Grounding", "NLI Entailment (<10%)", "Output DLP Redaction"],
  },
  {
    key: "security",
    titleKey: "architecture.sections.security",
    pillar: "security",
    icon: Lock,
    tags: ["PBKDF2 + Salt", "JWT HttpOnly Strict", "user_id Isolation", "Constant-Time Verification", "AES Vault"],
  },
  {
    key: "database",
    titleKey: "architecture.sections.database",
    pillar: "database",
    icon: Database,
    tags: ["SQLite Relational", "ChromaDB Vectors", "Neo4j 5.26 Cypher", "JSONL Corpora", "Multi-Session JSON"],
  },
  {
    key: "modelBackends",
    titleKey: "architecture.sections.modelBackends",
    pillar: "database",
    icon: Cpu,
    tags: ["Ollama / Local Stand-in", "Qwen 2.5 / DeepSeek", "OpenAI GPT-4o", "Claude 3.5 Sonnet", "Hot Switching"],
  },
  {
    key: "operations",
    titleKey: "architecture.sections.operations",
    pillar: "operations",
    icon: Activity,
    tags: ["Canonical config/", "3 Profiles", "Prometheus Metrics", "14 Grafana Panels", "Alertmanager", "Circuit Breakers"],
  },
  {
    key: "frontend",
    titleKey: "architecture.sections.frontend",
    pillar: "operations",
    icon: Layers,
    tags: ["React 18 + TS", "Vite 6.4", "Amber Tokens", "Critical CSS (-86%)", "Real-time SSE", "ReactFlow Canvas"],
  },
];

const KPI_ITEMS = [
  { valueKey: "architecture.kpi.accuracy", labelKey: "architecture.kpi.accuracyLabel", descKey: "architecture.kpi.accuracyDesc" },
  { valueKey: "architecture.kpi.hallucination", labelKey: "architecture.kpi.hallucinationLabel", descKey: "architecture.kpi.hallucinationDesc" },
  { valueKey: "architecture.kpi.citation", labelKey: "architecture.kpi.citationLabel", descKey: "architecture.kpi.citationDesc" },
  { valueKey: "architecture.kpi.latency", labelKey: "architecture.kpi.latencyLabel", descKey: "architecture.kpi.latencyDesc" },
  { valueKey: "architecture.kpi.memory", labelKey: "architecture.kpi.memoryLabel", descKey: "architecture.kpi.memoryDesc" },
  { valueKey: "architecture.kpi.coverage", labelKey: "architecture.kpi.coverageLabel", descKey: "architecture.kpi.coverageDesc" },
] as const;

const PILLAR_TABS: { id: PillarId; labelKey: string }[] = [
  { id: "all", labelKey: "architecture.tabs.all" },
  { id: "pipeline", labelKey: "architecture.tabs.pipeline" },
  { id: "retrieval", labelKey: "architecture.tabs.retrieval" },
  { id: "security", labelKey: "architecture.tabs.security" },
  { id: "database", labelKey: "architecture.tabs.database" },
  { id: "operations", labelKey: "architecture.tabs.operations" },
  { id: "endpoints", labelKey: "architecture.tabs.endpoints" },
];

const ENDPOINT_LINE_RE = /^([A-Z]+(?:\s*,\s*[A-Z]+)*)\s+(\S+)(?:\s*-\s*(.*))?$/;

function parseEndpoints(rawMarkdown: string): ParsedEndpoint[] {
  const lines = rawMarkdown.split("\n");
  let currentCategory = "General";
  const items: ParsedEndpoint[] = [];
  let counter = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith("#")) {
      currentCategory = trimmed.replace(/^#+\s*/, "").trim();
      continue;
    }
    const match = ENDPOINT_LINE_RE.exec(trimmed);
    if (match) {
      const methods = match[1]
        .split(",")
        .map((m) => m.trim())
        .filter(Boolean);
      const path = match[2].trim();
      const description = match[3]?.trim() || "";
      for (const method of methods) {
        counter++;
        items.push({
          id: `${method}-${path}-${counter}`,
          method,
          path,
          description,
          category: currentCategory,
        });
      }
    }
  }
  return items;
}

function getMethodBadgeClass(method: string): string {
  switch (method.toUpperCase()) {
    case "GET":
      return "bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/30";
    case "POST":
      return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30";
    case "PUT":
      return "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30";
    case "DELETE":
      return "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30";
    case "PATCH":
      return "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/30";
    default:
      return "bg-surface-muted text-ink-muted border-line";
  }
}

export function ArchitecturePage({ isLoggedIn }: Readonly<Props>) {
  const { t } = useTranslation();
  const [activePillar, setActivePillar] = useState<PillarId>("all");
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

  const visibleCards = useMemo(() => {
    if (activePillar === "all") return ARCHITECTURE_CARDS;
    if (activePillar === "endpoints") return [];
    return ARCHITECTURE_CARDS.filter((card) => card.pillar === activePillar);
  }, [activePillar]);

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      {/* Enterprise Header */}
      <header className="glass-panel border-x-0 border-t-0 p-4 sm:p-6">
        <div className="mx-auto flex max-w-[1720px] w-full flex-wrap items-start justify-between gap-4 px-2 sm:px-4">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="brand" size="pill" className="uppercase tracking-wider">
                {t("architecture.badges.enterprise")}
              </Badge>
              <Badge variant="neutral" size="pill" mono>
                {t("architecture.badges.version")}
              </Badge>
              <Badge variant="success" size="pill" className="gap-1.5">
                <span className="size-1.5 rounded-pill bg-success animate-pulse" aria-hidden="true" />
                {t("architecture.badges.status")}
              </Badge>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-4xl">QueryMind Architecture & Systems</h1>
            <p className="max-w-4xl text-sm sm:text-base text-ink-muted leading-relaxed">
              {t("dataFlow.description")}
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-ink-muted">
              <Badge variant="outline" size="sm" mono>
                {t("architecture.badges.stack")}
              </Badge>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <LanguageToggle />
            <Button asChild variant="secondary" size="sm">
              <Link to={isLoggedIn ? "/app" : "/app/login"}>{isLoggedIn ? t("nav.home") : t("auth.login")}</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container - Expands to use full screen width comfortably */}
      <main className="mx-auto w-full max-w-[1720px] space-y-8 px-2 sm:px-4 lg:px-6 py-6">
        {/* KPI Performance Highlights Banner */}
        <section aria-label="System Performance KPIs" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {KPI_ITEMS.map((kpi) => (
            <div
              key={kpi.valueKey}
              className="rounded-card border border-line bg-surface p-4 shadow-elev-1 transition-all hover:border-brand-border hover:shadow-elev-2"
            >
              <div className="font-mono text-2xl font-extrabold tracking-tight text-brand-text sm:text-3xl">
                {t(kpi.valueKey)}
              </div>
              <div className="mt-1.5 text-sm font-semibold text-ink">{t(kpi.labelKey)}</div>
              <div className="mt-1 text-xs text-ink-muted leading-relaxed">{t(kpi.descKey)}</div>
            </div>
          ))}
        </section>

        {/* Interactive Navigation Filter Tabs */}
        <nav aria-label="Architecture Pillars" className="flex flex-wrap items-center gap-2 border-b border-line pb-3">
          {PILLAR_TABS.map((tab) => {
            const isActive = activePillar === tab.id;
            return (
              <Button
                key={tab.id}
                variant={isActive ? "flat" : "ghost"}
                size="sm"
                onClick={() => setActivePillar(tab.id)}
                className="text-xs sm:text-sm font-medium py-2 px-3.5 transition-colors"
              >
                {t(tab.labelKey)}
              </Button>
            );
          })}
        </nav>

        {/* Section 1: End-to-End DataFlow Pipeline & Explorer */}
        {(activePillar === "all" || activePillar === "pipeline") && (
          <PipelineFlowDiagram />
        )}

        {/* Section 2: Architecture Pillars Cards Grid */}
        {visibleCards.length > 0 && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {visibleCards.map((card) => {
              const Icon = card.icon;
              const items = (t(`architecture.content.${card.key}`, { returnObjects: true }) as string[]) || [];

              return (
                <Card
                  key={card.key}
                  className="flex flex-col border-line bg-surface shadow-elev-1 transition-all duration-200 hover:border-brand-border hover:shadow-elev-2"
                >
                  <CardHeader className="border-b border-line/60 bg-surface-muted/30 p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="flex size-9 shrink-0 items-center justify-center rounded-control bg-brand-surface text-brand-text border border-brand-border">
                          <Icon className="size-4.5" aria-hidden="true" />
                        </div>
                        <CardTitle className="text-base sm:text-lg font-bold text-ink">{t(card.titleKey)}</CardTitle>
                      </div>
                      <Badge variant="neutral" size="sm" mono>
                        {items.length} items
                      </Badge>
                    </div>
                    {card.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-2.5">
                        {card.tags.map((tag) => (
                          <Badge key={tag} variant="outline" size="xs" mono className="text-xs py-0.5 px-2">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardHeader>
                  <CardContent className="flex-1 p-5">
                    <ul className="space-y-2.5">
                      {items.map((item) => (
                        <li key={item} className="flex items-start gap-2.5 text-sm leading-relaxed text-ink-muted">
                          <span className="mt-2 size-1.5 shrink-0 rounded-pill bg-brand-accent" aria-hidden="true" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Section 3: Interactive Full API Explorer */}
        {(activePillar === "all" || activePillar === "endpoints") && (
          <Card className="border-line shadow-elev-1 transition-all">
            <CardHeader className="border-b border-line bg-surface-muted/50 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-control bg-brand-surface text-brand-text border border-brand-border">
                    <Server className="size-4.5" aria-hidden="true" />
                  </div>
                  <div>
                    <CardTitle className="text-base sm:text-lg font-bold text-ink">{t("architecture.sections.keyEndpoints")}</CardTitle>
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
        )}
      </main>
    </div>
  );
}
