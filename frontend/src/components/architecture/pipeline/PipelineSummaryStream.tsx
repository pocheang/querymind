import {
  ArrowRight,
  CheckCircle2,
  Search,
  ShieldCheck,
  Sparkles,
  Workflow,
  Wrench,
} from "lucide-react";

interface PipelineSummaryStreamProps {
  isZh: boolean;
  t: (key: string) => string;
}

export function PipelineSummaryStream({
  isZh,
  t,
}: Readonly<PipelineSummaryStreamProps>) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2.5 rounded-control border border-line bg-surface-muted/40 p-4 text-sm text-ink-muted">
      <span className="font-bold text-ink">{isZh ? "全链路流转：" : "Full Data Stream:"}</span>
      <span className="flex items-center gap-1.5 font-medium">
        <ShieldCheck className="size-3.5 text-blue-500" />
        {t("architecture.flow.stages.step1.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Workflow className="size-3.5 text-cyan-500" />
        {t("architecture.flow.stages.step2.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Search className="size-3.5 text-emerald-500" />
        {t("architecture.flow.stages.step3.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Wrench className="size-3.5 text-amber-500" />
        {t("architecture.flow.stages.step4.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Sparkles className="size-3.5 text-purple-500" />
        {t("architecture.flow.stages.step5.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-bold text-brand-text">
        <CheckCircle2 className="size-3.5 text-rose-500" />
        {t("architecture.flow.stages.step6.role")}
      </span>
    </div>
  );
}
