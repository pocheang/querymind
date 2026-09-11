import { Images, Layers, Network, Sparkles, Table, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CardHeader, CardTitle } from "@/components/ui/card";
import type { ViewPerspective } from "./types";

interface PipelineFlowHeaderProps {
  perspective: ViewPerspective;
  setPerspective: (p: ViewPerspective) => void;
  t: (key: string) => string;
}

export function PipelineFlowHeader({
  perspective,
  setPerspective,
  t,
}: Readonly<PipelineFlowHeaderProps>) {
  return (
    <CardHeader className="flex flex-col gap-4 border-b border-line bg-surface-muted/40 p-5 sm:p-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1.5">
        <div className="flex items-center gap-2.5">
          <Layers className="size-5 text-brand-accent" aria-hidden="true" />
          <CardTitle className="text-lg sm:text-xl font-bold text-ink">
            {t("architecture.flow.title")}
          </CardTitle>
        </div>
        <p className="text-sm sm:text-base text-ink-muted leading-relaxed">
          {t("architecture.flow.subtitle")}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 rounded-control border border-line bg-surface p-1.5">
        <Button
          variant={perspective === "story" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("story")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Sparkles className="size-4 text-amber-500" />
          {t("architecture.flow.modeStory")}
        </Button>
        <Button
          variant={perspective === "tech" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("tech")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Zap className="size-4 text-brand-accent" />
          {t("architecture.flow.modeTech")}
        </Button>
        <Button
          variant={perspective === "table" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("table")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Table className="size-4 text-emerald-500" />
          {t("architecture.flow.modeTable")}
        </Button>
        <Button
          variant={perspective === "blueprint" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("blueprint")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Images className="size-4 text-blue-500" />
          {t("architecture.flow.modeBlueprint")}
        </Button>
        <Button
          variant={perspective === "topology" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("topology")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Network className="size-4 text-purple-500" />
          {t("architecture.flow.modeTopology")}
        </Button>
      </div>
    </CardHeader>
  );
}
