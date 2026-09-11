import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CardSectionConfig } from "./types";

interface ArchitectureCardsGridProps {
  cards: CardSectionConfig[];
}

export function ArchitectureCardsGrid({ cards }: Readonly<ArchitectureCardsGridProps>) {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
      {cards.map((card) => {
        const Icon = card.icon;
        const items = (t(`architecture.content.${card.key}`, { returnObjects: true }) as string[]) || [];

        return (
          <Card
            key={card.key}
            className="flex flex-col border-line bg-surface shadow-elev-1 transition-all duration-200 hover:border-brand-border hover:shadow-elev-2"
          >
            <CardHeader className="border-b border-line/60 bg-surface-muted/30 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-control bg-brand-surface text-brand-text border border-brand-border">
                    <Icon className="size-4.5" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-base sm:text-lg font-bold text-ink">{t(card.titleKey)}</CardTitle>
                </div>
                <Badge variant="neutral" size="sm" mono>
                  {items.length} items
                </Badge>
              </div>
              {card.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-2.5">
                  {card.tags.map((tag) => (
                    <Badge key={tag} variant="outline" size="xs" mono className="text-xs py-0.5 px-2">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </CardHeader>
            <CardContent className="flex-1 p-5">
              <ul className="space-y-2.5">
                {items.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm leading-relaxed text-ink-muted">
                    <span className="mt-2 size-1.5 shrink-0 rounded-pill bg-brand-accent" aria-hidden="true" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
