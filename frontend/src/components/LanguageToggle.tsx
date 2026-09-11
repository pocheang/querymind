import { useTranslation } from "react-i18next";
import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";

export function LanguageToggle() {
  const { i18n, t } = useTranslation();
  const isZh = Boolean(i18n.language?.startsWith("zh"));

  const toggleLanguage = () => {
    const newLang = isZh ? "en" : "zh";
    void i18n.changeLanguage(newLang);
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
      <span className="font-semibold">{isZh ? t("language.zh") : t("language.en")}</span>
    </Button>
  );
}
