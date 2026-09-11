import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Activity,
  ArrowRight,
  Brain,
  Check,
  CheckCircle2,
  Compass,
  Cpu,
  Database,
  ExternalLink,
  FileText,
  GitBranch,
  HelpCircle,
  Network,
  Search,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Zap,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LanguageToggle } from "@/components/LanguageToggle";
import { BrandMark } from "@/components/layout/BrandMark";
import { DataFlowVisualization } from "@/components/DataFlowVisualization";
import { FeatureDetailModal, type FeatureItem } from "@/pages/landing/FeatureDetailModal";

interface LandingPageProps {
  isLoggedIn: boolean;
}

function SectionHeading({ lead, accent, sub }: Readonly<{ lead: string; accent: string; sub: string }>) {
  return (
    <div className="mx-auto max-w-3xl space-y-2.5 text-center">
      <h2 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl lg:text-4xl">
        {lead} <span className="text-brand-text">{accent}</span>
      </h2>
      <p className="text-sm leading-relaxed text-ink/80 sm:text-base">{sub}</p>
    </div>
  );
}

export function LandingPage({ isLoggedIn }: Readonly<LandingPageProps>) {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<"chat" | "graph" | "metrics">("chat");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [activeFeature, setActiveFeature] = useState<FeatureItem | null>(null);

  useEffect(() => {
    document.title = `${t("app.title")} - ${t("app.subtitle")}`;
  }, [i18n.language, t]);

  const navLinks = [
    { href: "#features", label: t("pages.landing.navFeatures") },
    { href: "#workflow", label: t("pages.landing.navWorkflow") },
    { href: "#agents", label: t("pages.landing.navAgents") },
    { href: "#architecture", label: t("pages.landing.navArchitecture") },
  ];

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

  const agentCards = [
    {
      key: "",
      icon: Compass,
      title: t("pages.landing.agentAutoTitle"),
      desc: t("pages.landing.agentAutoDesc"),
      badge: t("pages.landing.agentAutoBadge"),
      featured: true,
      accent: "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      capabilities: [
        t("pages.landing.agentAutoCap1"),
        t("pages.landing.agentAutoCap2"),
        t("pages.landing.agentAutoCap3"),
        t("pages.landing.agentAutoCap4"),
      ],
      link: "/app",
      actionText: t("pages.landing.agentAutoAction"),
    },
    {
      key: "cybersecurity",
      icon: ShieldCheck,
      title: t("pages.landing.agentCyberTitle"),
      desc: t("pages.landing.agentCyberDesc"),
      badge: t("pages.landing.agentCyberBadge"),
      featured: false,
      accent: "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20",
      capabilities: [
        t("pages.landing.agentCyberCap1"),
        t("pages.landing.agentCyberCap2"),
        t("pages.landing.agentCyberCap3"),
        t("pages.landing.agentCyberCap4"),
      ],
      link: "/app?mode=cybersecurity",
      actionText: t("pages.landing.agentCyberAction"),
    },
    {
      key: "artificial_intelligence",
      icon: Brain,
      title: t("pages.landing.agentAiTitle"),
      desc: t("pages.landing.agentAiDesc"),
      badge: t("pages.landing.agentAiBadge"),
      featured: false,
      accent: "text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/20",
      capabilities: [
        t("pages.landing.agentAiCap1"),
        t("pages.landing.agentAiCap2"),
        t("pages.landing.agentAiCap3"),
        t("pages.landing.agentAiCap4"),
      ],
      link: "/app?mode=artificial_intelligence",
      actionText: t("pages.landing.agentAiAction"),
    },
    {
      key: "pdf_text",
      icon: FileText,
      title: t("pages.landing.agentPdfTitle"),
      desc: t("pages.landing.agentPdfDesc"),
      badge: t("pages.landing.agentPdfBadge"),
      featured: false,
      accent: "text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
      capabilities: [
        t("pages.landing.agentPdfCap1"),
        t("pages.landing.agentPdfCap2"),
        t("pages.landing.agentPdfCap3"),
        t("pages.landing.agentPdfCap4"),
      ],
      link: "/app?mode=pdf_text",
      actionText: t("pages.landing.agentPdfAction"),
    },
    {
      key: "general",
      icon: Sparkles,
      title: t("pages.landing.agentGeneralTitle"),
      desc: t("pages.landing.agentGeneralDesc"),
      badge: t("pages.landing.agentGeneralBadge"),
      featured: false,
      accent: "text-purple-600 dark:text-purple-400 bg-purple-500/10 border-purple-500/20",
      capabilities: [
        t("pages.landing.agentGeneralCap1"),
        t("pages.landing.agentGeneralCap2"),
        t("pages.landing.agentGeneralCap3"),
        t("pages.landing.agentGeneralCap4"),
      ],
      link: "/app?mode=general",
      actionText: t("pages.landing.agentGeneralAction"),
    },
  ];

  const workflow = [
    {
      icon: Shield,
      title: t("pages.landing.step1Title"),
      body: t("pages.landing.step1Body"),
      tag: t("pages.landing.step1Tag"),
    },
    {
      icon: Compass,
      title: t("pages.landing.step2Title"),
      body: t("pages.landing.step2Body"),
      tag: t("pages.landing.step2Tag"),
    },
    {
      icon: Search,
      title: t("pages.landing.step3Title"),
      body: t("pages.landing.step3Body"),
      tag: t("pages.landing.step3Tag"),
    },
    {
      icon: Sparkles,
      title: t("pages.landing.step4Title"),
      body: t("pages.landing.step4Body"),
      tag: t("pages.landing.step4Tag"),
    },
  ];

  const trustMetrics = [
    { value: "100%", label: t("pages.landing.trustPrivate"), desc: t("pages.landing.trustPrivateDesc") },
    { value: "< 800ms", label: t("pages.landing.trustLatency"), desc: t("pages.landing.trustLatencyDesc") },
    { value: "99.8%", label: t("pages.landing.trustGrounding"), desc: t("pages.landing.trustGroundingDesc") },
    { value: "0 依赖", label: t("pages.landing.trustZeroDeps"), desc: t("pages.landing.trustZeroDepsDesc") },
  ];

  return (
    <div className="landing-root aurora-bg min-h-screen">
      {/* Top Navigation */}
      <header className="glass-panel sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-x-0 border-t-0 px-4 shadow-elev-1 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <BrandMark />
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold tracking-tight text-ink sm:text-base">{t("app.title")}</span>
            <Badge variant="brand" size="xs" mono className="text-xs uppercase font-medium px-1.5 py-0.5">
              v0.7
            </Badge>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Main Navigation">
          {navLinks.map(({ href, label }) => (
            <a
              key={href}
              href={href}
              className="rounded-control px-3 py-1.5 text-xs font-medium text-ink/80 transition-colors hover:bg-brand-surface hover:text-brand-text sm:text-sm"
            >
              {label}
            </a>
          ))}
          <Link
            to="/app/architecture"
            className="flex items-center gap-1.5 rounded-control px-3 py-1.5 text-xs font-medium text-ink/80 transition-colors hover:bg-brand-surface hover:text-brand-text sm:text-sm"
          >
            <span>{t("dataFlow.title", "架构流转")}</span>
            <ExternalLink className="size-3.5 opacity-70" aria-hidden="true" />
          </Link>
        </nav>

        <div className="flex items-center gap-1.5">
          <LanguageToggle />
          {isLoggedIn ? (
            <Button asChild size="sm">
              <Link to="/app" className="gap-1.5 text-xs sm:text-sm font-semibold">
                <span>{t("pages.landing.enterApp")}</span>
                <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="secondary" size="sm">
                <Link to="/app/login?mode=login" className="text-xs sm:text-sm font-semibold">{t("auth.login")}</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/app/login?mode=register" className="text-xs sm:text-sm font-semibold">{t("pages.landing.register")}</Link>
              </Button>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative mx-auto max-w-5xl px-4 pt-12 pb-16 text-center sm:pt-20 sm:pb-24">
        {/* Floating Top Pill */}
        <div className="mb-6 flex justify-center">
          <div className="inline-flex items-center gap-2 rounded-pill border border-brand-border bg-brand-surface/80 px-3.5 py-1.5 text-xs font-medium text-brand-text shadow-xs backdrop-blur-sm sm:text-sm">
            <Sparkles className="size-3.5 text-brand" aria-hidden="true" />
            <span>Agentic RAG · 企业私有知识库智能问答与多跳图谱推理</span>
            <span className="hidden rounded bg-brand/10 px-2 py-0.5 text-xs font-semibold uppercase sm:inline">
              Production Ready
            </span>
          </div>
        </div>

        <h1 className="text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl lg:text-6xl">
          {t("pages.landing.heroName")}
          <br />
          <span className="bg-[image:var(--brand-gradient)] bg-clip-text text-transparent">
            {t("pages.landing.heroTagline")}
          </span>
        </h1>

        <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-ink/80 sm:text-base">
          {t("pages.landing.heroSubtitle")}
        </p>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2.5">
          {isLoggedIn ? (
            <Button asChild size="lg" className="gap-1.5 shadow-elev-2 text-sm sm:text-base">
              <Link to="/app">
                {t("pages.landing.enterApp")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </Button>
          ) : (
            <>
              <Button asChild size="lg" className="gap-1.5 shadow-elev-2 text-sm sm:text-base">
                <Link to="/app/login?mode=login">
                  {t("auth.login")}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="secondary" className="text-sm sm:text-base">
                <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
              </Button>
            </>
          )}
          <Button asChild size="lg" variant="ghost" className="text-sm sm:text-base">
            <a href="#features" className="gap-1">
              <span>{t("pages.landing.learnMore")}</span>
            </a>
          </Button>
        </div>

        {/* Live Interactive Product Preview Card */}
        <div className="mt-12 overflow-hidden rounded-panel border border-line-subtle bg-surface/80 shadow-elev-3 backdrop-blur-md transition-all sm:mt-16">
          {/* Mock Window Top Bar */}
          <div className="flex items-center justify-between border-b border-line-subtle bg-surface-muted/60 px-4 py-3 text-xs text-ink-muted sm:text-sm">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5" aria-hidden="true">
                <span className="size-2.5 rounded-pill bg-danger/80" />
                <span className="size-2.5 rounded-pill bg-warning/80" />
                <span className="size-2.5 rounded-pill bg-success/80" />
              </div>
              <span className="ml-2 font-mono text-xs text-ink/70">
                querymind-deck://session/enterprise-kb-v4
              </span>
            </div>

            {/* Interactive Preview Switch Tabs */}
            <div className="flex items-center rounded-control border border-line-subtle bg-surface p-1 text-xs">
              <button
                type="button"
                onClick={() => setActiveTab("chat")}
                className={cn(
                  "rounded px-3 py-1 font-medium transition-colors text-xs",
                  activeTab === "chat" ? "bg-brand text-white shadow-xs" : "text-ink/70 hover:text-ink"
                )}
              >
                {t("pages.landing.demoTabChat")}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("graph")}
                className={cn(
                  "rounded px-3 py-1 font-medium transition-colors text-xs",
                  activeTab === "graph" ? "bg-brand text-white shadow-xs" : "text-ink/70 hover:text-ink"
                )}
              >
                {t("pages.landing.demoTabGraph")}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("metrics")}
                className={cn(
                  "rounded px-3 py-1 font-medium transition-colors text-xs",
                  activeTab === "metrics" ? "bg-brand text-white shadow-xs" : "text-ink/70 hover:text-ink"
                )}
              >
                {t("pages.landing.demoTabMetrics")}
              </button>
            </div>
          </div>

          {/* Mock Console Content Body */}
          <div className="p-4 text-left sm:p-6">
            {activeTab === "chat" && (
              <div className="space-y-4">
                {/* User Query Bubble */}
                <div className="flex items-start gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-brand-surface font-bold text-brand-text text-xs sm:text-sm">
                    U
                  </div>
                  <div className="rounded-panel rounded-tl-sm bg-surface-muted p-3.5 text-sm font-medium leading-relaxed text-ink">
                    请分析企业私有知识库在金融合规场景下，如何结合向量检索与知识图谱进行多跳事实核验？
                  </div>
                </div>

                {/* Execution Trace Live Stepper */}
                <div className="ml-11 rounded-card border border-line-subtle bg-surface-inset/60 p-3">
                  <div className="flex flex-wrap items-center gap-2.5 text-xs font-medium text-ink/80">
                    <span className="flex items-center gap-1.5 font-semibold text-success">
                      <CheckCircle2 className="size-3.5" />
                      路由决策: 混合深度 (Deep RAG)
                    </span>
                    <span className="text-line-strong">&bull;</span>
                    <span className="flex items-center gap-1.5">
                      <Database className="size-3.5 text-brand" />
                      ChromaDB 向量 (top_k=10)
                    </span>
                    <span className="text-line-strong">&bull;</span>
                    <span className="flex items-center gap-1.5">
                      <Network className="size-3.5 text-blue-500" />
                      Neo4j 图谱 (3 跳实体关联)
                    </span>
                    <span className="text-line-strong">&bull;</span>
                    <span className="font-mono text-ink/70">耗时: 1.42s</span>
                  </div>
                </div>

                {/* Assistant Answer Bubble with Grounding */}
                <div className="flex items-start gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-[image:var(--brand-gradient)] text-white text-xs sm:text-sm font-bold shadow-xs">
                    AI
                  </div>
                  <div className="space-y-2.5 rounded-panel rounded-tl-sm border border-line-subtle bg-surface p-4 text-sm leading-relaxed text-ink shadow-xs">
                    <p className="leading-relaxed text-ink font-normal">
                      在金融级知识库中，系统采用<strong>双路融合验证机制</strong>：
                    </p>
                    <ol className="list-decimal space-y-1.5 pl-4 text-xs leading-relaxed text-ink/85 sm:text-sm">
                      <li>
                        <strong>密集语义匹配</strong>：ChromaDB 检索制度文档与监管条款，计算上下文相似度<span className="ml-1 cursor-pointer font-mono font-bold text-brand-text hover:underline">[1]</span>。
                      </li>
                      <li>
                        <strong>知识图谱实体穿透</strong>：Neo4j 遍历“金融产品 - 关联机构 -担保关系”多跳拓扑，检测隐式违规链条<span className="ml-1 cursor-pointer font-mono font-bold text-brand-text hover:underline">[2]</span>。
                      </li>
                      <li>
                        <strong>严谨性校验与输出脱敏</strong>：Synthesizer 配合 Verifier 过滤幻觉，并在 chunk 边界通过 DLP 引擎实时抹除账户敏感信息。
                      </li>
                    </ol>

                    <div className="flex flex-wrap items-center gap-2.5 pt-2.5 border-t border-line-subtle text-xs">
                      <Badge variant="success" size="xs" mono className="text-xs font-semibold px-2 py-0.5">
                        Grounding: 99.8%
                      </Badge>
                      <Badge variant="brand" size="xs" mono className="text-xs font-semibold px-2 py-0.5">
                        BGE-Reranker Score: 0.94
                      </Badge>
                      <span className="text-xs font-medium text-ink/75">数据源：内部监管制度汇编.pdf · Neo4j 拓扑网</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "graph" && (
              <div className="space-y-3 py-4 text-center">
                <div className="mx-auto flex max-w-md items-center justify-center gap-3 py-6">
                  <div className="rounded-card border border-blue-500/30 bg-blue-500/10 p-3.5 text-center">
                    <Network className="mx-auto size-6 text-blue-500" />
                    <span className="mt-1.5 block text-sm font-bold text-ink">实体: 银保信披准则</span>
                    <span className="text-xs font-medium text-ink/70">Node: Regulation</span>
                  </div>
                  <div className="h-0.5 w-12 bg-blue-500/40 relative">
                    <span className="absolute -top-3 left-1 text-xs font-mono font-semibold text-ink/70">APPLIES_TO</span>
                  </div>
                  <div className="rounded-card border border-amber-500/30 bg-amber-500/10 p-3.5 text-center">
                    <Database className="mx-auto size-6 text-amber-500" />
                    <span className="mt-1.5 block text-sm font-bold text-ink">业务: 财富信托计划</span>
                    <span className="text-xs font-medium text-ink/70">Node: Product</span>
                  </div>
                  <div className="h-0.5 w-12 bg-amber-500/40 relative">
                    <span className="absolute -top-3 left-1 text-xs font-mono font-semibold text-ink/70">GOVERNED_BY</span>
                  </div>
                  <div className="rounded-card border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-center">
                    <ShieldCheck className="mx-auto size-6 text-emerald-500" />
                    <span className="mt-1.5 block text-sm font-bold text-ink">审计: 反洗钱审查</span>
                    <span className="text-xs font-medium text-ink/70">Node: AuditEvent</span>
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-ink/80 sm:text-sm">
                  Neo4j 多跳关系推理引擎正在运行，自动解析深层因果关系与非显式实体网络。
                </p>
              </div>
            )}

            {activeTab === "metrics" && (
              <div className="grid grid-cols-2 gap-3 py-3 sm:grid-cols-4">
                <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                  <span className="text-xs font-medium text-ink/80 sm:text-sm">平均首字延迟</span>
                  <p className="mt-1 font-mono text-xl font-bold text-brand-text sm:text-2xl">420ms</p>
                  <span className="text-xs font-semibold text-success">高于同类架构 3.2x</span>
                </div>
                <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                  <span className="text-xs font-medium text-ink/80 sm:text-sm">混合检索命中率</span>
                  <p className="mt-1 font-mono text-xl font-bold text-brand-text sm:text-2xl">98.4%</p>
                  <span className="text-xs font-semibold text-success">RRF 倒数融合增益</span>
                </div>
                <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                  <span className="text-xs font-medium text-ink/80 sm:text-sm">流式解析吞吐</span>
                  <p className="mt-1 font-mono text-xl font-bold text-brand-text sm:text-2xl">48 tok/s</p>
                  <span className="text-xs font-medium text-ink/70">本地并发安全</span>
                </div>
                <div className="rounded-card border border-line-subtle bg-surface p-3.5 text-center">
                  <span className="text-xs font-medium text-ink/80 sm:text-sm">外部泄露防护</span>
                  <p className="mt-1 font-mono text-xl font-bold text-success sm:text-2xl">100% 零外传</p>
                  <span className="text-xs font-medium text-ink/70">Air-Gapped 兼容</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Trust Metrics Bar */}
        <div className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {trustMetrics.map((item) => (
            <div
              key={item.label}
              className="rounded-card border border-line-subtle bg-surface/60 p-4 text-center shadow-xs backdrop-blur-sm transition-all hover:bg-surface"
            >
              <div className="font-mono text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
                <span className="bg-[image:var(--brand-gradient)] bg-clip-text text-transparent">{item.value}</span>
              </div>
              <div className="mt-1.5 text-sm font-bold text-ink sm:text-base">{item.label}</div>
              <div className="mt-1 text-xs leading-relaxed text-ink/75 sm:text-sm">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Twelve Pillars Capabilities Section */}
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
                onClick={() => setActiveFeature(feature)}
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
                      setActiveFeature(feature);
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

      {/* Specialized Agent Modes Section */}
      <section id="agents" className="mx-auto max-w-5xl space-y-8 px-4 py-14">
        <SectionHeading
          lead={t("pages.landing.agentsHeadingLead")}
          accent={t("pages.landing.agentsHeadingAccent")}
          sub={t("pages.landing.agentsSubtitle")}
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agentCards.map((agent) => {
            const Icon = agent.icon;
            return (
              <Card
                key={agent.title}
                className={cn(
                  "relative flex flex-col justify-between space-y-4 p-5 sm:p-6 transition-all hover:shadow-elev-2",
                  agent.featured && "border-2 border-brand-border-strong bg-brand-surface/40 shadow-elev-2"
                )}
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-control border shadow-xs", agent.accent)}>
                        <Icon className="size-4.5" aria-hidden="true" />
                      </span>
                      <h3 className="text-base font-bold text-ink">{agent.title}</h3>
                    </div>
                    <Badge variant={agent.featured ? "brand" : "neutral"} size="xs" className="text-xs font-semibold px-2 py-0.5">
                      {agent.badge}
                    </Badge>
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-ink/80 sm:text-sm">{agent.desc}</p>

                  <ul className="mt-4 space-y-2.5 border-t border-line-subtle pt-3.5">
                    {agent.capabilities.map((label) => (
                      <li
                        key={label}
                        className="flex items-start gap-2.5 text-xs font-medium leading-relaxed text-ink/90 sm:text-sm"
                      >
                        <Check
                          className="mt-0.5 size-4 shrink-0 rounded-pill bg-success p-0.5 text-white"
                          strokeWidth={3}
                          aria-hidden="true"
                        />
                        <span>{label}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-3">
                  <Button asChild variant={agent.featured ? "default" : "secondary"} size="sm" className="w-full shadow-xs text-xs sm:text-sm font-semibold">
                    <Link to={agent.link} className="gap-1.5">
                      <span>{agent.actionText}</span>
                      <ArrowRight className="size-3.5" aria-hidden="true" />
                    </Link>
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Dynamic Dispatch Note & Single Console Experience CTA */}
        <div className="flex flex-col items-center justify-between gap-4 rounded-card border border-line-subtle bg-surface/70 p-4 shadow-xs backdrop-blur-sm sm:flex-row sm:p-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-control bg-brand-surface text-brand-text">
              <Cpu className="size-5" aria-hidden="true" />
            </div>
            <div className="text-left">
              <h4 className="text-sm font-bold text-ink sm:text-base">{t("pages.landing.agentsBannerTitle")}</h4>
              <p className="mt-1 text-xs leading-relaxed text-ink/80 sm:text-sm">
                {t("pages.landing.agentsBannerDesc")}
              </p>
            </div>
          </div>
          <Button asChild size="sm" className="shrink-0 shadow-xs text-xs sm:text-sm font-semibold">
            <Link to="/app" className="gap-1.5">
              <span>{t("pages.landing.enterApp")}</span>
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Execution Workflow Section */}
      <section id="workflow" className="mx-auto max-w-4xl space-y-8 px-4 py-14">
        <SectionHeading lead={t("pages.landing.workflowTitle")} accent="" sub={t("pages.landing.workflowSubtitle")} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {workflow.map(({ icon: Icon, title, body, tag }, index) => (
            <Card key={title} className="p-5 sm:p-6 transition-all hover:border-brand-border-strong hover:shadow-elev-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2.5">
                  <span className="flex size-8 items-center justify-center rounded-control bg-brand-surface text-brand-text">
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <span className="font-mono text-sm font-bold text-brand-accent sm:text-base">
                    STEP {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <Badge variant="neutral" size="xs" className="text-xs font-semibold px-2 py-0.5">
                  {tag}
                </Badge>
              </div>
              <h4 className="mt-3 text-sm font-bold text-ink sm:text-base">{title}</h4>
              <p className="mt-1.5 text-xs leading-relaxed text-ink/80 sm:text-sm">{body}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* Full-stack System Architecture Section */}
      <section id="architecture" className="mx-auto max-w-5xl space-y-8 px-4 py-14">
        <SectionHeading
          lead={t("pages.landing.archHeadingLead")}
          accent={t("pages.landing.archHeadingAccent")}
          sub={t("pages.landing.archSubtitle")}
        />
        <Card className="relative overflow-hidden shadow-elev-2">
          <div className="absolute right-3 top-3 z-10 flex items-center gap-2">
            <Badge variant="brand" size="pill" className="text-xs font-medium px-2.5 py-0.5">
              {t("pages.landing.archPreviewHint")}
            </Badge>
            <Button asChild variant="secondary" size="xs" className="text-xs font-medium">
              <Link to="/app/architecture" className="gap-1.5">
                <span>{t("pages.landing.fullscreenArch")}</span>
                <ExternalLink className="size-3" />
              </Link>
            </Button>
          </div>
          <DataFlowVisualization />
        </Card>
      </section>

      {/* Call to Action Banner */}
      <section className="mx-auto max-w-5xl px-4 py-14">
        <div className="rounded-panel bg-[image:var(--brand-gradient)] p-8 text-center text-white shadow-elev-3 sm:p-12">
          <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-pill bg-white/15 backdrop-blur-sm">
            <Zap className="size-6 text-white" aria-hidden="true" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl lg:text-4xl">{t("pages.landing.ctaTitle")}</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/90 sm:text-base">
            {t("pages.landing.ctaSubtitle")}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            {isLoggedIn ? (
              <Button asChild size="lg" variant="secondary" className="shadow-elev-2 text-sm sm:text-base">
                <Link to="/app" className="gap-1.5">
                  <span>{t("pages.landing.enterApp")}</span>
                  <ArrowRight className="size-4" aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" variant="secondary" className="shadow-elev-2 text-sm sm:text-base">
                  <Link to="/app/login?mode=login" className="gap-1.5">
                    <span>{t("auth.loginButton")}</span>
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="ghost"
                  className="border border-white/40 text-white hover:bg-white/15 hover:text-white text-sm sm:text-base"
                >
                  <Link to="/app/login?mode=register">{t("pages.landing.register")}</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-line-subtle px-4 py-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-2">
            <BrandMark size="sm" />
            <span className="text-sm font-bold text-ink">QueryMind 智询</span>
            <span className="text-xs font-medium text-ink-muted">· Enterprise Agentic RAG</span>
          </div>

          <nav className="flex flex-wrap items-center justify-center gap-5 text-xs font-medium text-ink/80 sm:text-sm">
            <a href="#features" className="hover:text-brand-text transition-colors">
              {t("pages.landing.navFeatures")}
            </a>
            <a href="#workflow" className="hover:text-brand-text transition-colors">
              {t("pages.landing.footerFlow")}
            </a>
            <a href="#agents" className="hover:text-brand-text transition-colors">
              {t("pages.landing.footerAgents")}
            </a>
            <Link to="/app/architecture" className="hover:text-brand-text transition-colors">
              {t("dataFlow.title")}
            </Link>
          </nav>

          <p className="text-xs text-ink/75">
            &copy; {new Date().getFullYear()} {t("app.title")}. All rights reserved.
          </p>
        </div>
      </footer>

      {/* Technical Deep Dive Detail Modal */}
      <FeatureDetailModal
        feature={activeFeature}
        isOpen={activeFeature !== null}
        onClose={() => setActiveFeature(null)}
      />
    </div>
  );
}
