import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Activity,
  ArrowRight,
  Brain,
  Cpu,
  Database,
  FileText,
  GitBranch,
  HelpCircle,
  Network,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { SectionHeading } from "./SectionHeading";
import type { FeatureItem } from "./types";

interface LandingFeaturesSectionProps {
  onSelectFeature: (feature: FeatureItem) => void;
}

export function LandingFeaturesSection({ onSelectFeature }: Readonly<LandingFeaturesSectionProps>) {
  const { t } = useTranslation();
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const featureCategories = [
    { key: "all", label: t("pages.landing.featureCatAll") },
    { key: "core", label: t("pages.landing.featureCatCore") },
    { key: "data", label: t("pages.landing.featureCatData") },
    { key: "interaction", label: t("pages.landing.featureCatInteraction") },
    { key: "ops", label: t("pages.landing.featureCatOps") },
  ];

  const features: FeatureItem[] = [
    {
      category: "core",
      icon: Brain,
      title: t("pages.landing.feature1Title"),
      desc: t("pages.landing.feature1Desc"),
      badge: "LangGraph",
      accent: "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      sourceFile: "app/orchestration/langgraph/workflow.py",
      pipelineFlow: t("pages.landing.feature1Flow"),
      technicalMechanism: t("pages.landing.feature1Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature1Spec1"),
        t("pages.landing.feature1Spec2"),
        t("pages.landing.feature1Spec3"),
      ],
    },
    {
      category: "core",
      icon: Search,
      title: t("pages.landing.feature2Title"),
      desc: t("pages.landing.feature2Desc"),
      badge: "ChromaDB + BM25",
      accent: "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      sourceFile: "app/retrievers/hybrid/fusion.py",
      pipelineFlow: t("pages.landing.feature2Flow"),
      technicalMechanism: t("pages.landing.feature2Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature2Spec1"),
        t("pages.landing.feature2Spec2"),
        t("pages.landing.feature2Spec3"),
      ],
    },
    {
      category: "core",
      icon: Network,
      title: t("pages.landing.feature3Title"),
      desc: t("pages.landing.feature3Desc"),
      badge: "Neo4j Graph RAG",
      accent: "text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/20",
      sourceFile: "app/graph/knowledge/client.py",
      pipelineFlow: t("pages.landing.feature3Flow"),
      technicalMechanism: t("pages.landing.feature3Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature3Spec1"),
        t("pages.landing.feature3Spec2"),
        t("pages.landing.feature3Spec3"),
      ],
    },
    {
      category: "core",
      icon: GitBranch,
      title: t("pages.landing.feature4Title"),
      desc: t("pages.landing.feature4Desc"),
      badge: "Self-RAG & Verifier",
      accent: "text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
      sourceFile: "app/services/query/decomposer.py",
      pipelineFlow: t("pages.landing.feature4Flow"),
      technicalMechanism: t("pages.landing.feature4Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature4Spec1"),
        t("pages.landing.feature4Spec2"),
        t("pages.landing.feature4Spec3"),
      ],
    },
    {
      category: "data",
      icon: FileText,
      title: t("pages.landing.feature5Title"),
      desc: t("pages.landing.feature5Desc"),
      badge: "Stream PDF + OCR",
      accent: "text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
      sourceFile: "app/ingestion/loaders/pdf_stream.py",
      pipelineFlow: t("pages.landing.feature5Flow"),
      technicalMechanism: t("pages.landing.feature5Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature5Spec1"),
        t("pages.landing.feature5Spec2"),
        t("pages.landing.feature5Spec3"),
      ],
    },
    {
      category: "data",
      icon: Database,
      title: t("pages.landing.feature6Title"),
      desc: t("pages.landing.feature6Desc"),
      badge: "Sync Connectors",
      accent: "text-teal-600 dark:text-teal-400 bg-teal-500/10 border-teal-500/20",
      sourceFile: "app/services/connectors/registry.py",
      pipelineFlow: t("pages.landing.feature6Flow"),
      technicalMechanism: t("pages.landing.feature6Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature6Spec1"),
        t("pages.landing.feature6Spec2"),
        t("pages.landing.feature6Spec3"),
      ],
    },
    {
      category: "data",
      icon: SlidersHorizontal,
      title: t("pages.landing.feature7Title"),
      desc: t("pages.landing.feature7Desc"),
      badge: "Context & Budget",
      accent: "text-sky-600 dark:text-sky-400 bg-sky-500/10 border-sky-500/20",
      sourceFile: "app/services/context_management.py",
      pipelineFlow: t("pages.landing.feature7Flow"),
      technicalMechanism: t("pages.landing.feature7Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature7Spec1"),
        t("pages.landing.feature7Spec2"),
        t("pages.landing.feature7Spec3"),
      ],
    },
    {
      category: "interaction",
      icon: Cpu,
      title: t("pages.landing.feature8Title"),
      desc: t("pages.landing.feature8Desc"),
      badge: "MCP Standard + HITL",
      accent: "text-purple-600 dark:text-purple-400 bg-purple-500/10 border-purple-500/20",
      sourceFile: "app/mcp/gateway.py",
      pipelineFlow: t("pages.landing.feature8Flow"),
      technicalMechanism: t("pages.landing.feature8Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature8Spec1"),
        t("pages.landing.feature8Spec2"),
        t("pages.landing.feature8Spec3"),
      ],
    },
    {
      category: "interaction",
      icon: Sparkles,
      title: t("pages.landing.feature9Title"),
      desc: t("pages.landing.feature9Desc"),
      badge: "Long-Term Memory",
      accent: "text-fuchsia-600 dark:text-fuchsia-400 bg-fuchsia-500/10 border-fuchsia-500/20",
      sourceFile: "app/memory/long_term.py",
      pipelineFlow: t("pages.landing.feature9Flow"),
      technicalMechanism: t("pages.landing.feature9Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature9Spec1"),
        t("pages.landing.feature9Spec2"),
        t("pages.landing.feature9Spec3"),
      ],
    },
    {
      category: "interaction",
      icon: HelpCircle,
      title: t("pages.landing.feature10Title"),
      desc: t("pages.landing.feature10Desc"),
      badge: "Clarification Agent",
      accent: "text-orange-600 dark:text-orange-400 bg-orange-500/10 border-orange-500/20",
      sourceFile: "app/services/query/clarification.py",
      pipelineFlow: t("pages.landing.feature10Flow"),
      technicalMechanism: t("pages.landing.feature10Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature10Spec1"),
        t("pages.landing.feature10Spec2"),
        t("pages.landing.feature10Spec3"),
      ],
    },
    {
      category: "ops",
      icon: Activity,
      title: t("pages.landing.feature11Title"),
      desc: t("pages.landing.feature11Desc"),
      badge: "Circuit Breaker & Ops",
      accent: "text-violet-600 dark:text-violet-400 bg-violet-500/10 border-violet-500/20",
      sourceFile: "app/services/runtime/resilience.py",
      pipelineFlow: t("pages.landing.feature11Flow"),
      technicalMechanism: t("pages.landing.feature11Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature11Spec1"),
        t("pages.landing.feature11Spec2"),
        t("pages.landing.feature11Spec3"),
      ],
    },
    {
      category: "ops",
      icon: ShieldCheck,
      title: t("pages.landing.feature12Title"),
      desc: t("pages.landing.feature12Desc"),
      badge: "RBAC & DLP Zero-Trust",
      accent: "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20",
      sourceFile: "app/services/security/sanitization.py",
      pipelineFlow: t("pages.landing.feature12Flow"),
      technicalMechanism: t("pages.landing.feature12Mechanism"),
      engineeringSpecs: [
        t("pages.landing.feature12Spec1"),
        t("pages.landing.feature12Spec2"),
        t("pages.landing.feature12Spec3"),
      ],
    },
  ];

  const filteredFeatures =
    selectedCategory === "all"
      ? features
      : features.filter((f) => f.category === selectedCategory);

  return (
    <section id="features" className="mx-auto max-w-6xl space-y-8 px-4 py-14">
      <SectionHeading
        lead={t("pages.landing.featuresHeadingLead")}
        accent={t("pages.landing.featuresHeadingAccent")}
        sub={t("pages.landing.featuresSubtitle")}
      />

      {/* Category Filter Pills */}
      <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
        {featureCategories.map((cat) => {
          const count = cat.key === "all" ? features.length : features.filter((f) => f.category === cat.key).length;
          const isSelected = selectedCategory === cat.key;
          return (
            <button
              key={cat.key}
              type="button"
              onClick={() => setSelectedCategory(cat.key)}
              className={cn(
                "rounded-full px-4 py-1.5 text-xs sm:text-sm font-medium transition-all",
                isSelected
                  ? "bg-brand text-white shadow-xs"
                  : "border border-line-subtle bg-surface/70 text-ink-muted hover:border-brand-border-strong hover:text-ink"
              )}
            >
              <span>{cat.label}</span>
              <span className={cn("ml-1.5 text-xs font-semibold", isSelected ? "text-white/90" : "text-ink-faint")}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {filteredFeatures.map((feature) => {
          const { icon: Icon, title, desc, badge, accent, sourceFile } = feature;
          return (
            <Card
              key={title}
              onClick={() => onSelectFeature(feature)}
              className="group relative flex flex-col justify-between p-6 transition-all hover:-translate-y-0.5 hover:border-brand-border-strong hover:shadow-elev-2 cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className={cn("flex size-10 items-center justify-center rounded-card border shadow-xs", accent)}>
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <Badge variant="neutral" size="xs" mono className="text-xs font-medium px-2 py-0.5">
                    {badge}
                  </Badge>
                </div>
                <h3 className="mt-4 text-base font-bold text-ink transition-colors group-hover:text-brand-text">
                  {title}
                </h3>
                <p className="mt-2 text-xs sm:text-sm leading-relaxed text-ink/80">{desc}</p>
              </div>

              <div className="mt-5 flex items-center justify-between pt-3 border-t border-line-subtle/60 text-xs">
                <span className="font-mono text-ink-muted font-medium transition-colors">
                  {sourceFile.split("/").pop()}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectFeature(feature);
                  }}
                  className="flex items-center gap-1.5 font-semibold text-brand-text transition-colors hover:underline"
                >
                  <span>{t("pages.landing.featureExplore")}</span>
                  <ArrowRight className="size-3.5" aria-hidden="true" />
                </button>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
