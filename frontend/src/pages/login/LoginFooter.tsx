import { useTranslation } from "react-i18next";

export function LoginFooter() {
  const { t } = useTranslation();

  return (
    <footer className="relative z-10 w-full max-w-[1220px] mx-auto py-1 sm:py-1.5 text-center text-xs text-stone-500 space-y-1">
      <div className="font-semibold text-stone-700">
        {t("pages.login.footerLine1")}
      </div>
      <div className="text-xs text-stone-500 font-normal">
        {t("pages.login.footerLine2")}
      </div>
    </footer>
  );
}
