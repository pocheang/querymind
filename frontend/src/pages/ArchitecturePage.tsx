import { useMemo, useState } from "react";
import { PipelineFlowDiagram } from "@/components/architecture/PipelineFlowDiagram";

import { ArchitectureHeader } from "./architecture/ArchitectureHeader";
import { ArchitectureKpiBanner } from "./architecture/ArchitectureKpiBanner";
import { ArchitecturePillarTabs } from "./architecture/ArchitecturePillarTabs";
import { ArchitectureCardsGrid } from "./architecture/ArchitectureCardsGrid";
import { ArchitectureApiExplorer } from "./architecture/ArchitectureApiExplorer";
import { ARCHITECTURE_CARDS, type PillarId } from "./architecture/types";

type Props = {
  isLoggedIn: boolean;
};

export function ArchitecturePage({ isLoggedIn }: Readonly<Props>) {
  const [activePillar, setActivePillar] = useState<PillarId>("all");

  const visibleCards = useMemo(() => {
    if (activePillar === "all") return ARCHITECTURE_CARDS;
    if (activePillar === "endpoints") return [];
    return ARCHITECTURE_CARDS.filter((card) => card.pillar === activePillar);
  }, [activePillar]);

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      {/* Enterprise Header */}
      <ArchitectureHeader isLoggedIn={isLoggedIn} />

      {/* Main Container */}
      <main className="mx-auto w-full max-w-[1720px] space-y-8 px-2 sm:px-4 lg:px-6 py-6">
        {/* KPI Performance Highlights Banner */}
        <ArchitectureKpiBanner />

        {/* Interactive Navigation Filter Tabs */}
        <ArchitecturePillarTabs
          activePillar={activePillar}
          onSelectPillar={setActivePillar}
        />

        {/* Section 1: End-to-End DataFlow Pipeline & Explorer */}
        {(activePillar === "all" || activePillar === "pipeline") && (
          <PipelineFlowDiagram />
        )}

        {/* Section 2: Architecture Pillars Cards Grid */}
        {visibleCards.length > 0 && (
          <ArchitectureCardsGrid cards={visibleCards} />
        )}

        {/* Section 3: Interactive Full API Explorer */}
        {(activePillar === "all" || activePillar === "endpoints") && (
          <ArchitectureApiExplorer />
        )}
      </main>
    </div>
  );
}
