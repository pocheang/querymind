import { Boxes, Search, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { BrandMark } from "@/components/layout/BrandMark";

export function LoginShowcasePanel() {
  const { t } = useTranslation();

  return (
    <section className="relative hidden md:col-span-6 md:flex flex-col justify-between overflow-hidden bg-gradient-to-br from-amber-50/90 via-[#fffdf9] to-amber-100/50 p-6 lg:p-7 xl:p-8 border-r border-amber-200/80">
      {/* Internal ambient illumination */}
      <div className="pointer-events-none absolute -right-20 -top-20 size-80 rounded-full bg-amber-400/20 blur-3xl" />
      <div className="pointer-events-none absolute -left-20 -bottom-20 size-80 rounded-full bg-orange-400/15 blur-3xl" />

      {/* Top Brand Header & Status Pill */}
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BrandMark size="sm" />
          <span className="text-sm sm:text-base font-extrabold tracking-tight text-stone-900">
            {t("app.title")}
          </span>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-100/90 px-2.5 py-0.5 text-xs font-bold text-amber-900 shadow-xs">
          <span className="size-2 rounded-full bg-amber-500 animate-pulse" />
          {t("pages.login.localReady")}
        </span>
      </div>

      {/* Central Pitch & Enterprise Features */}
      <div className="relative z-10 my-auto space-y-3.5 py-2">
        <div className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/50 bg-amber-100/80 px-2.5 py-0.5 text-xs font-bold text-amber-900">
          <span>✦ Next-Gen Agentic RAG</span>
        </div>

        <h1 className="text-2xl lg:text-[28px] xl:text-3xl font-black leading-snug tracking-tight text-stone-900">
          {t("pages.login.headline")
            .split("\n")
            .join(" · ")}
        </h1>

        <p className="text-xs sm:text-sm leading-relaxed text-stone-700 font-medium max-w-lg">
          {t("pages.login.missionDesc")}
        </p>

        {/* 3 Streamlined High-Contrast Enterprise Feature Cards */}
        <div className="space-y-2 pt-1">
          <div className="flex items-start gap-3 rounded-xl border border-amber-200/90 bg-white/95 p-2.5 sm:p-3 shadow-xs transition-all hover:shadow-sm hover:border-amber-300">
            <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 text-white shadow-xs shrink-0">
              <Boxes className="size-4" />
            </div>
            <div className="space-y-1">
              <div className="text-xs sm:text-sm font-bold text-stone-900">
                {t("features.multiAgent")}
              </div>
              <div className="text-xs text-stone-600 leading-normal font-normal">
                {t("pages.login.multiAgentDesc")}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-xl border border-amber-200/90 bg-white/95 p-2.5 sm:p-3 shadow-xs transition-all hover:shadow-sm hover:border-amber-300">
            <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 text-white shadow-xs shrink-0">
              <Search className="size-4" />
            </div>
            <div className="space-y-1">
              <div className="text-xs sm:text-sm font-bold text-stone-900">
                {t("features.hybridSearch")}
              </div>
              <div className="text-xs text-stone-600 leading-normal font-normal">
                {t("pages.login.hybridSearchDesc")}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-xl border border-amber-200/90 bg-white/95 p-2.5 sm:p-3 shadow-xs transition-all hover:shadow-sm hover:border-amber-300">
            <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 text-white shadow-xs shrink-0">
              <ShieldCheck className="size-4" />
            </div>
            <div className="space-y-1">
              <div className="text-xs sm:text-sm font-bold text-stone-900">
                {t("features.enterpriseSecurity")}
              </div>
              <div className="text-xs text-stone-600 leading-normal font-normal">
                {t("pages.login.securityDesc")}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Enterprise SLA Readout Card */}
      <div className="relative z-10 rounded-xl border border-amber-200/90 bg-white/95 py-2 px-3 shadow-xs grid grid-cols-3 divide-x divide-amber-200 text-center">
        <div className="space-y-0.5">
          <div className="text-lg sm:text-xl font-black text-amber-700">99.1%</div>
          <div className="text-xs font-bold text-stone-700">{t("pages.login.intentRecall")}</div>
        </div>
        <div className="space-y-0.5">
          <div className="text-lg sm:text-xl font-black text-amber-700">&lt;420ms</div>
          <div className="text-xs font-bold text-stone-700">{t("pages.login.streamingLatency")}</div>
        </div>
        <div className="space-y-0.5">
          <div className="text-lg sm:text-xl font-black text-amber-700">100%</div>
          <div className="text-xs font-bold text-stone-700">{t("pages.login.tenantIsolation")}</div>
        </div>
      </div>
    </section>
  );
}
