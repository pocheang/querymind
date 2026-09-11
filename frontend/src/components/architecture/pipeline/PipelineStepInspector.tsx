import { Check, Sparkles, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { StepConfig } from "./types";

interface PipelineStepInspectorProps {
  currentFocusedStep: StepConfig;
  isZh: boolean;
  t: (key: string) => string;
}

export function PipelineStepInspector({
  currentFocusedStep,
  isZh,
  t,
}: Readonly<PipelineStepInspectorProps>) {
  return (
    <div className="rounded-control border border-line bg-surface-muted/30 p-5 space-y-3.5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className={`flex size-7 items-center justify-center rounded-control ${currentFocusedStep.iconBg}`}>
            <currentFocusedStep.icon className="size-4" />
          </div>
          <span className="text-sm sm:text-base font-bold text-ink">
            {t("architecture.flow.step")} 0{currentFocusedStep.id} · {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.role`)}
          </span>
          <span className="text-xs sm:text-sm text-ink-muted font-mono">
            ({t(`architecture.flow.stages.${currentFocusedStep.stepKey}.techTitle`)})
          </span>
        </div>
        <Badge variant="neutral" size="sm" mono className="text-xs py-1 px-2.5">
          {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.badge`)}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
        <div className="space-y-2">
          <div className="font-semibold text-brand-text flex items-center gap-1.5 text-sm sm:text-base">
            <Sparkles className="size-4 text-amber-500" />
            {t("architecture.flow.explanation")}
          </div>
          <p className="text-ink-muted leading-relaxed text-sm sm:text-base">
            {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.storyDesc`)}
          </p>
          <p className="text-xs sm:text-sm text-ink-muted italic border-l-2 border-brand-border pl-2.5">
            💡 {isZh ? currentFocusedStep.analogyZh : currentFocusedStep.analogyEn}
          </p>
        </div>

        <div className="space-y-2">
          <div className="font-semibold text-brand-text flex items-center gap-1.5 text-sm sm:text-base">
            <Zap className="size-4 text-brand-accent" />
            {t("architecture.flow.techSpecification")}
          </div>
          <p className="text-ink-muted leading-relaxed font-mono text-xs sm:text-sm">
            {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.techDesc`)}
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1.5">
            {(isZh ? currentFocusedStep.keyPointsZh : currentFocusedStep.keyPointsEn).map((pt) => (
              <span
                key={pt}
                className="inline-flex items-center gap-1 text-xs text-ink-muted bg-surface border border-line rounded px-2 py-1"
              >
                <Check className="size-3 text-emerald-500" />
                {pt}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
