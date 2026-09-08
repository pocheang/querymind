import { useTranslation } from "react-i18next";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";

type Props = {
  sectionsHidden: boolean;
  onToggle: () => void;
};

export function SectionToggleButton({ sectionsHidden, onToggle }: Readonly<Props>) {
  const { t } = useTranslation();
  const label = sectionsHidden ? t("components.chat.showSections") : t("components.chat.hideSections");

  return (
    <Button
      variant="secondary"
      size="sm"
      className="fixed right-4 top-[4.25rem] z-30 shadow-elev-2"
      onClick={onToggle}
      title={label}
      aria-label={label}
      aria-pressed={sectionsHidden}
    >
      {sectionsHidden ? (
        <Eye className="size-3.5" aria-hidden="true" />
      ) : (
        <EyeOff className="size-3.5" aria-hidden="true" />
      )}
      <span className="hidden sm:inline">{label}</span>
    </Button>
  );
}
