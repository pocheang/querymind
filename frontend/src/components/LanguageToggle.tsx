import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";

export function LanguageToggle() {
  const { i18n, t } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === "en" ? "zh" : "en";
    i18n.changeLanguage(newLang);
    localStorage.setItem("language", newLang);
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={toggleLanguage}
      title={t("language.toggle")}
      aria-label={t("language.toggle")}
    >
      <Languages className="size-3.5 text-brand-accent" aria-hidden="true" />
      <span className="font-semibold">{i18n.language === "en" ? t("language.en") : t("language.zh")}</span>
    </Button>
  );
}
