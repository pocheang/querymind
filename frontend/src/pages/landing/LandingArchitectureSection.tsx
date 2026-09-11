import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DataFlowVisualization } from "@/components/DataFlowVisualization";
import { SectionHeading } from "./SectionHeading";

export function LandingArchitectureSection() {
  const { t } = useTranslation();

  return (
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
  );
}
