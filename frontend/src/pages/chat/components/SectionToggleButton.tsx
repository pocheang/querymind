import { useTranslation } from "react-i18next";
import { Eye } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  sectionsHidden: boolean;
  onToggle: () => void;
};

/**
 * When the input area (composer & runtime panels) is collapsed, this floating
 * icon button appears at the bottom center of the viewport to allow one-click restore.
 * When the composer is visible, the collapse control lives directly inside the composer's
 * own toolbar so nothing intrusively floats over top chat messages.
 */
export function SectionToggleButton({ sectionsHidden, onToggle }: Readonly<Props>) {
  const { t } = useTranslation();

  if (!sectionsHidden) return null;

  const label = t("components.chat.showSections");

  return (
    <Button
      variant="secondary"
      size="icon"
      className="fixed bottom-5 left-1/2 -translate-x-1/2 z-30 size-9 rounded-pill border border-line bg-surface/95 text-ink shadow-elev-3 backdrop-blur-md transition-all hover:scale-110 hover:bg-surface hover:text-brand-text active:scale-95"
      onClick={onToggle}
      title={label}
      aria-label={label}
      aria-pressed={sectionsHidden}
    >
      <Eye className="size-4 text-brand-text" aria-hidden="true" />
    </Button>
  );
}
