import { useTranslation } from "react-i18next";
import { BrandMark } from "@/components/layout/BrandMark";
import { LanguageToggle } from "@/components/LanguageToggle";

export function LoginHeader() {
  const { t } = useTranslation();

  return (
    <header className="relative z-20 flex items-center justify-between w-full max-w-[1220px] mx-auto py-1 sm:py-1.5 px-2">
      <div className="flex items-center gap-3">
        <BrandMark size="sm" />
        <div className="flex items-baseline gap-2">
          <span className="text-base sm:text-lg font-extrabold tracking-tight text-stone-900">
            {t("app.title")}
          </span>
          <span className="hidden sm:inline-block text-xs sm:text-sm font-semibold text-amber-800/80">
            {t("app.subtitle")}
          </span>
        </div>
      </div>
      <LanguageToggle />
    </header>
  );
}
