import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { PILLAR_TABS, type PillarId } from "./types";

interface ArchitecturePillarTabsProps {
  activePillar: PillarId;
  onSelectPillar: (pillar: PillarId) => void;
}

export function ArchitecturePillarTabs({
  activePillar,
  onSelectPillar,
}: Readonly<ArchitecturePillarTabsProps>) {
  const { t } = useTranslation();

  return (
    <nav aria-label="Architecture Pillars" className="flex flex-wrap items-center gap-2 border-b border-line pb-3">
      {PILLAR_TABS.map((tab) => {
        const isActive = activePillar === tab.id;
        return (
          <Button
            key={tab.id}
            variant={isActive ? "flat" : "ghost"}
            size="sm"
            onClick={() => onSelectPillar(tab.id)}
            className="text-xs sm:text-sm font-medium py-2 px-3.5 transition-colors"
          >
            {t(tab.labelKey)}
          </Button>
        );
      })}
    </nav>
  );
}
