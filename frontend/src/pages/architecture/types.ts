import {
  Activity,
  Cpu,
  Database,
  FileText,
  Layers,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

export type PillarId = "all" | "pipeline" | "retrieval" | "security" | "database" | "operations" | "endpoints";

export interface CardSectionConfig {
  key: string;
  titleKey: string;
  pillar: PillarId;
  icon: React.ComponentType<{ className?: string }>;
  tags: string[];
}

export interface ParsedEndpoint {
  id: string;
  method: string;
  path: string;
  description: string;
  category: string;
}

export const ARCHITECTURE_CARDS: CardSectionConfig[] = [
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

export const KPI_ITEMS = [
  { valueKey: "architecture.kpi.accuracy", labelKey: "architecture.kpi.accuracyLabel", descKey: "architecture.kpi.accuracyDesc" },
  { valueKey: "architecture.kpi.hallucination", labelKey: "architecture.kpi.hallucinationLabel", descKey: "architecture.kpi.hallucinationDesc" },
  { valueKey: "architecture.kpi.citation", labelKey: "architecture.kpi.citationLabel", descKey: "architecture.kpi.citationDesc" },
  { valueKey: "architecture.kpi.latency", labelKey: "architecture.kpi.latencyLabel", descKey: "architecture.kpi.latencyDesc" },
  { valueKey: "architecture.kpi.memory", labelKey: "architecture.kpi.memoryLabel", descKey: "architecture.kpi.memoryDesc" },
  { valueKey: "architecture.kpi.coverage", labelKey: "architecture.kpi.coverageLabel", descKey: "architecture.kpi.coverageDesc" },
] as const;

export const PILLAR_TABS: { id: PillarId; labelKey: string }[] = [
  { id: "all", labelKey: "architecture.tabs.all" },
  { id: "pipeline", labelKey: "architecture.tabs.pipeline" },
  { id: "retrieval", labelKey: "architecture.tabs.retrieval" },
  { id: "security", labelKey: "architecture.tabs.security" },
  { id: "database", labelKey: "architecture.tabs.database" },
  { id: "operations", labelKey: "architecture.tabs.operations" },
  { id: "endpoints", labelKey: "architecture.tabs.endpoints" },
];

function parseEndpointLine(line: string): { methods: string[]; path: string; description: string } | null {
  const dashIndex = line.indexOf(" - ");
  const head = dashIndex !== -1 ? line.slice(0, dashIndex).trim() : line.trim();
  const description = dashIndex !== -1 ? line.slice(dashIndex + 3).trim() : "";

  const firstSlash = head.indexOf("/");
  if (firstSlash <= 0) return null;

  const methodPart = head.slice(0, firstSlash).trim();
  const path = head.slice(firstSlash).trim();
  if (!methodPart || !path) return null;

  const methods = methodPart.split(",").map((m) => m.trim()).filter(Boolean);
  if (methods.length === 0 || !methods.every((m) => /^[A-Z]+$/.test(m))) {
    return null;
  }
  return { methods, path, description };
}

export function parseEndpoints(rawMarkdown: string): ParsedEndpoint[] {
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
    const parsed = parseEndpointLine(trimmed);
    if (parsed) {
      for (const method of parsed.methods) {
        counter++;
        items.push({
          id: `${method}-${parsed.path}-${counter}`,
          method,
          path: parsed.path,
          description: parsed.description,
          category: currentCategory,
        });
      }
    }
  }
  return items;
}

export function getMethodBadgeClass(method: string): string {
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
