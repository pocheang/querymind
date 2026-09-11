import { Play, Radio, RotateCcw, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ScenarioKey, StepConfig } from "./types";

interface PipelineSimulationBarProps {
  selectedScenario: ScenarioKey;
  setSelectedScenario: (sc: ScenarioKey) => void;
  isSimulating: boolean;
  runSimulation: () => void;
  resetSimulation: () => void;
  isZh: boolean;
  t: (key: string) => string;
}

export function PipelineSimulationBar({
  selectedScenario,
  setSelectedScenario,
  isSimulating,
  runSimulation,
  resetSimulation,
  isZh,
  t,
}: Readonly<PipelineSimulationBarProps>) {
  return (
    <div className="rounded-card border border-brand-border bg-surface-muted/40 p-5 shadow-elev-1">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-line/60 pb-3.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-sm font-semibold text-ink flex items-center gap-2">
            <Radio className="size-4 text-brand-accent animate-pulse" />
            {t("architecture.flow.sampleQueryLabel")}：
          </span>
          {(["rag", "react", "graph"] as ScenarioKey[]).map((scKey) => (
            <Button
              key={scKey}
              variant={selectedScenario === scKey ? "flat" : "secondary"}
              size="sm"
              onClick={() => setSelectedScenario(scKey)}
              disabled={isSimulating}
              className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3.5"
            >
              {t(`architecture.flow.scenarios.${scKey}.title`)}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2.5 self-end sm:self-auto">
          <Button
            variant="default"
            size="sm"
            onClick={runSimulation}
            disabled={isSimulating}
            className="gap-2 text-xs sm:text-sm font-semibold py-2 px-4 shadow-sm"
          >
            <Play className="size-3.5" />
            {isSimulating ? t("architecture.flow.simulating") : t("architecture.flow.runSim")}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={resetSimulation}
            disabled={isSimulating}
            title={t("architecture.flow.resetSim")}
          >
            <RotateCcw className="size-4 text-ink-muted" />
          </Button>
        </div>
      </div>

      <div className="mt-4 flex items-start gap-3.5">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-control bg-brand-surface border border-brand-border text-brand-text">
          <User className="size-4.5" />
        </div>
        <div className="flex-1 space-y-1.5">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-ink-muted">
              {isZh ? "用户发送的问题" : "User Chat Input"}
            </span>
            <Badge variant="brand" size="xs" mono className="text-xs py-0.5 px-2 font-medium">
              {t(`architecture.flow.scenarios.${selectedScenario}.tag`)}
            </Badge>
          </div>
          <p className="text-base sm:text-lg font-medium text-ink bg-surface border border-line/60 rounded-control px-4 py-3 shadow-inner leading-relaxed">
            “{t(`architecture.flow.scenarios.${selectedScenario}.query`)}”
          </p>
        </div>
      </div>
    </div>
  );
}

interface PipelineSimulationProgressProps {
  activeStepConfig: StepConfig;
  isZh: boolean;
  t: (key: string) => string;
}

export function PipelineSimulationProgress({
  activeStepConfig,
  isZh,
  t,
}: Readonly<PipelineSimulationProgressProps>) {
  return (
    <div className="rounded-control border border-brand-accent/50 bg-brand-surface/80 p-4 shadow-elev-2 animate-in fade-in slide-in-from-top-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex size-3 rounded-full bg-brand-accent animate-ping" />
          <Badge variant="brand" size="sm" mono className="font-bold text-xs py-1 px-2.5">
            {t("architecture.flow.step")} {activeStepConfig.id} / 6
          </Badge>
          <span className="text-sm sm:text-base font-semibold text-ink">
            {isZh ? activeStepConfig.simStatusZh : activeStepConfig.simStatusEn}
          </span>
        </div>
        <Badge variant="neutral" size="sm" mono className="text-xs py-1 px-2.5">
          {t(`architecture.flow.stages.${activeStepConfig.stepKey}.badge`)}
        </Badge>
      </div>

      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface">
        <div
          className="h-full bg-brand-accent transition-all duration-700 ease-out"
          style={{ width: `${(activeStepConfig.id / 6) * 100}%` }}
        />
      </div>
    </div>
  );
}
