import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  PipelineAnswerShowcase,
  PipelineBlueprintView,
  PipelineFlowHeader,
  PipelineSimulationBar,
  PipelineSimulationProgress,
  PipelineStepCard,
  PipelineStepInspector,
  PipelineSummaryStream,
  PipelineTableView,
  PipelineTopologyView,
  STEPS,
  type ScenarioKey,
  type ViewPerspective,
} from "./pipeline";

export function PipelineFlowDiagram() {
  const { t, i18n } = useTranslation();
  const isZh = Boolean(i18n?.language?.startsWith("zh"));

  const [perspective, setPerspective] = useState<ViewPerspective>("story");
  const [selectedScenario, setSelectedScenario] = useState<ScenarioKey>("rag");
  const [activeStepIndex, setActiveStepIndex] = useState<number | null>(null);
  const [focusedStepId, setFocusedStepId] = useState<number>(1);
  const [isSimulating, setIsSimulating] = useState(false);
  const [hasCompletedOnce, setHasCompletedOnce] = useState(false);

  const runSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setHasCompletedOnce(false);
    setActiveStepIndex(0);
    setFocusedStepId(1);

    let step = 0;
    const totalSteps = STEPS.length;

    const timer = setInterval(() => {
      step++;
      if (step < totalSteps) {
        setActiveStepIndex(step);
        setFocusedStepId(STEPS[step].id);
      } else {
        clearInterval(timer);
        setIsSimulating(false);
        setActiveStepIndex(null);
        setHasCompletedOnce(true);
      }
    }, 1100);
  };

  const resetSimulation = () => {
    setIsSimulating(false);
    setActiveStepIndex(null);
    setFocusedStepId(1);
    setHasCompletedOnce(false);
  };

  useEffect(() => {
    resetSimulation();
  }, [selectedScenario]);

  const activeStepConfig = useMemo(() => {
    if (activeStepIndex === null) return null;
    return STEPS[activeStepIndex] || null;
  }, [activeStepIndex]);

  const currentFocusedStep = useMemo(() => {
    return STEPS.find((s) => s.id === focusedStepId) || STEPS[0];
  }, [focusedStepId]);

  return (
    <Card className="overflow-hidden border-line shadow-elev-1 transition-all">
      <PipelineFlowHeader perspective={perspective} setPerspective={setPerspective} t={t} />

      <CardContent className="p-5 sm:p-6">
        {perspective === "blueprint" && <PipelineBlueprintView isZh={isZh} />}
        {perspective === "table" && <PipelineTableView isZh={isZh} t={t} />}
        {perspective === "topology" && <PipelineTopologyView t={t} />}

        {(perspective === "story" || perspective === "tech") && (
          <div className="space-y-7">
            <PipelineSimulationBar
              selectedScenario={selectedScenario}
              setSelectedScenario={setSelectedScenario}
              isSimulating={isSimulating}
              runSimulation={runSimulation}
              resetSimulation={resetSimulation}
              isZh={isZh}
              t={t}
            />

            {isSimulating && activeStepConfig && (
              <PipelineSimulationProgress activeStepConfig={activeStepConfig} isZh={isZh} t={t} />
            )}

            <div>
              <div className="mb-3.5 flex items-center justify-between text-sm text-ink-muted">
                <span className="font-semibold text-ink flex items-center gap-2 text-base">
                  <ArrowRight className="size-4 text-brand-accent" />
                  {isZh ? "AI 内部流转的 6 个执行阶段" : "6 Sequential Execution Phases Inside AI"}
                </span>
                <span className="text-xs text-ink-faint">
                  {t("architecture.flow.clickHint")}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {STEPS.map((stg) => {
                  const isCurrentActive = activeStepConfig?.id === stg.id;
                  const isPastCompleted =
                    isSimulating && activeStepConfig ? activeStepConfig.id > stg.id : false;
                  const isFocused = focusedStepId === stg.id;

                  return (
                    <PipelineStepCard
                      key={stg.id}
                      stg={stg}
                      isCurrentActive={isCurrentActive}
                      isPastCompleted={isPastCompleted}
                      hasCompletedOnce={hasCompletedOnce}
                      isFocused={isFocused}
                      perspective={perspective}
                      isZh={isZh}
                      onSelect={setFocusedStepId}
                      t={t}
                    />
                  );
                })}
              </div>
            </div>

            <PipelineStepInspector currentFocusedStep={currentFocusedStep} isZh={isZh} t={t} />
            <PipelineAnswerShowcase selectedScenario={selectedScenario} isZh={isZh} t={t} />
            <PipelineSummaryStream isZh={isZh} t={t} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
