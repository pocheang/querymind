import { Check, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getCardStateClass, type StepConfig, type ViewPerspective } from "./types";

interface StepBadgeProps {
  isCurrentActive: boolean;
  isPastCompleted: boolean;
  hasCompletedOnce: boolean;
  badgeText: string;
  activeStepText: string;
  completeStepText: string;
}

export function StepBadge({
  isCurrentActive,
  isPastCompleted,
  hasCompletedOnce,
  badgeText,
  activeStepText,
  completeStepText,
}: Readonly<StepBadgeProps>) {
  if (isCurrentActive) {
    return (
      <Badge variant="brand" size="xs" mono className="text-xs py-0.5 px-2 animate-pulse font-semibold">
        {activeStepText}
      </Badge>
    );
  }
  if (isPastCompleted || hasCompletedOnce) {
    return (
      <Badge
        variant="outline"
        size="xs"
        mono
        className="text-xs py-0.5 px-2 text-emerald-600 dark:text-emerald-400 border-emerald-500/40 bg-emerald-500/10 font-semibold"
      >
        <Check className="mr-1 size-3" />
        {completeStepText}
      </Badge>
    );
  }
  return (
    <Badge variant="neutral" size="xs" mono className="text-xs py-0.5 px-2">
      {badgeText}
    </Badge>
  );
}

interface PipelineStepCardProps {
  stg: StepConfig;
  isCurrentActive: boolean;
  isPastCompleted: boolean;
  hasCompletedOnce: boolean;
  isFocused: boolean;
  perspective: ViewPerspective;
  isZh: boolean;
  onSelect: (id: number) => void;
  t: (key: string) => string;
}

export function PipelineStepCard({
  stg,
  isCurrentActive,
  isPastCompleted,
  hasCompletedOnce,
  isFocused,
  perspective,
  isZh,
  onSelect,
  t,
}: Readonly<PipelineStepCardProps>) {
  const Icon = stg.icon;
  const roleTitle = t(`architecture.flow.stages.${stg.stepKey}.role`);
  const techTitle = t(`architecture.flow.stages.${stg.stepKey}.techTitle`);
  const storyDesc = t(`architecture.flow.stages.${stg.stepKey}.storyDesc`);
  const techDesc = t(`architecture.flow.stages.${stg.stepKey}.techDesc`);
  const badgeText = t(`architecture.flow.stages.${stg.stepKey}.badge`);
  const keyPoints = isZh ? stg.keyPointsZh : stg.keyPointsEn;
  const cardBorder = getCardStateClass(isCurrentActive, isFocused);

  return (
    <button
      type="button"
      onClick={() => onSelect(stg.id)}
      className={`group relative flex w-full cursor-pointer flex-col rounded-card border text-left transition-all duration-200 ${cardBorder}`}
    >
      {/* Step Header */}
      <div className="flex items-center justify-between gap-3 border-b border-line/60 bg-surface-muted/30 p-4">
        <div className="flex items-center gap-3">
          <div className={`flex size-9 items-center justify-center rounded-control border ${stg.badgeClass}`}>
            <Icon className="size-4.5" aria-hidden="true" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-bold text-ink leading-snug">
              {perspective === "story" ? roleTitle : techTitle}
            </div>
            <div className="text-xs font-mono text-ink-muted leading-snug">
              {perspective === "story" ? techTitle : roleTitle}
            </div>
          </div>
        </div>

        <StepBadge
          isCurrentActive={isCurrentActive}
          isPastCompleted={isPastCompleted}
          hasCompletedOnce={hasCompletedOnce}
          badgeText={badgeText}
          activeStepText={t("architecture.flow.activeStep")}
          completeStepText={t("architecture.flow.completeStep")}
        />
      </div>

      {/* Step Body */}
      <div className="flex-1 p-4 space-y-3">
        <div className="text-sm text-ink-muted leading-relaxed">
          {perspective === "story" ? (
            <>
              <p className="font-medium text-ink leading-relaxed text-sm sm:text-base">{storyDesc}</p>
              <p className="mt-2 text-xs sm:text-sm text-ink-muted border-l-2 border-brand-border pl-2.5 leading-relaxed">
                💡 {isZh ? stg.analogyZh : stg.analogyEn}
              </p>
            </>
          ) : (
            <p className="font-medium text-ink leading-relaxed text-sm sm:text-base">{techDesc}</p>
          )}
        </div>

        {/* Feature Badges */}
        <div className="flex flex-wrap gap-1.5 pt-1.5">
          {keyPoints.map((point) => (
            <Badge
              key={point}
              variant="outline"
              size="xs"
              mono
              className="text-xs py-0.5 px-2 bg-surface-muted/60 text-ink-muted"
            >
              {point}
            </Badge>
          ))}
        </div>
      </div>

      {/* Card Footer */}
      <div className="border-t border-line/40 px-4 py-2 flex items-center justify-between text-xs">
        <span className="font-mono text-ink-faint">
          {t("architecture.flow.step")} 0{stg.id} / 06
        </span>
        <span className="font-mono text-ink-muted flex items-center gap-1.5">
          <Clock className="size-3" />
          {badgeText}
        </span>
      </div>
    </button>
  );
}
