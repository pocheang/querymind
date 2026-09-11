import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  CheckCircle2,
  Code2,
  ExternalLink,
  GitCommit,
  Layers,
  LucideIcon,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface FeatureItem {
  category: "core" | "data" | "interaction" | "ops";
  icon: LucideIcon;
  title: string;
  desc: string;
  badge: string;
  accent: string;
  sourceFile: string;
  pipelineFlow: string;
  technicalMechanism: string;
  engineeringSpecs: string[];
}

interface FeatureDetailModalProps {
  feature: FeatureItem | null;
  isOpen: boolean;
  onClose: () => void;
}

export function FeatureDetailModal({ feature, isOpen, onClose }: Readonly<FeatureDetailModalProps>) {
  const { t } = useTranslation();

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !feature) return null;

  const Icon = feature.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label={t("pages.landing.featureModalClose")}
        className="fixed inset-0 bg-stone-900/60 backdrop-blur-sm animate-in fade-in duration-200 border-0 cursor-default"
        onClick={onClose}
        tabIndex={-1}
      />
      <dialog
        open
        aria-labelledby="feature-detail-title"
        className="relative z-10 m-0 flex w-full max-w-3xl max-h-[90vh] flex-col overflow-hidden rounded-panel border border-line-subtle bg-surface p-0 text-ink shadow-elev-3 animate-in zoom-in-95 duration-200 backdrop:bg-transparent"
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-line-subtle bg-surface-muted/50 p-5 sm:p-6">
          <div className="flex items-center gap-3.5">
            <span className={cn("flex size-12 items-center justify-center rounded-card border shadow-xs", feature.accent)}>
              <Icon className="size-6" aria-hidden="true" />
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 id="feature-detail-title" className="text-lg font-bold text-ink sm:text-xl">
                  {feature.title}
                </h3>
                <Badge variant="neutral" size="xs" mono className="text-xs font-semibold px-2.5 py-0.5">
                  {feature.badge}
                </Badge>
              </div>
              <p className="mt-1 text-xs sm:text-sm text-ink-muted">{t("pages.landing.featureModalTitle")}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("pages.landing.featureModalClose")}
            className="rounded-control p-2 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div className="flex-1 space-y-6 overflow-y-auto p-5 sm:p-6 leading-relaxed">
          {/* Execution Pipeline Flow */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-bold text-ink">
              <Layers className="size-4 text-brand-text" aria-hidden="true" />
              <span>{t("pages.landing.featureModalFlow")}</span>
            </div>
            <div className="rounded-card border border-line-subtle bg-surface-muted/40 p-3.5 font-mono text-xs sm:text-sm text-ink">
              <div className="flex flex-wrap items-center gap-2">
                {feature.pipelineFlow.split("➔").map((step, idx, arr) => (
                  <span key={step.trim()} className="flex items-center gap-2">
                    <span className="rounded bg-surface px-3 py-1 font-semibold text-ink shadow-xs border border-line-subtle">
                      {step.trim()}
                    </span>
                    {idx < arr.length - 1 && <span className="text-brand-text font-bold text-sm">➔</span>}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Technical Mechanism */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-bold text-ink">
              <GitCommit className="size-4 text-brand-text" aria-hidden="true" />
              <span>{t("pages.landing.featureModalDesc")}</span>
            </div>
            <p className="rounded-card border border-line-subtle bg-surface/80 p-4 text-sm sm:text-base leading-relaxed text-ink">
              {feature.technicalMechanism}
            </p>
          </div>

          {/* Source Code File Location */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-bold text-ink">
              <Code2 className="size-4 text-brand-text" aria-hidden="true" />
              <span>{t("pages.landing.featureModalSource")}</span>
            </div>
            <div className="flex items-center justify-between rounded-card border border-line-subtle bg-surface-muted/60 px-4 py-2.5 font-mono text-xs sm:text-sm">
              <span className="text-ink font-semibold select-all">{feature.sourceFile}</span>
              <Badge variant="brand" size="xs" mono className="text-xs font-semibold px-2.5 py-0.5">
                Production Verified
              </Badge>
            </div>
          </div>

          {/* Key Engineering Specifications */}
          <div className="space-y-2.5">
            <span className="text-sm font-bold text-ink">
              {t("pages.landing.featureModalSpecs")}
            </span>
            <ul className="grid grid-cols-1 gap-2.5">
              {feature.engineeringSpecs.map((spec) => (
                <li
                  key={spec}
                  className="flex items-start gap-2.5 rounded-card border border-line-subtle/80 bg-surface/60 p-3"
                >
                  <CheckCircle2 className="mt-0.5 size-4.5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                  <span className="text-ink text-xs sm:text-sm font-medium leading-normal">{spec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-line-subtle bg-surface-muted/40 p-4 sm:p-5">
          <Button asChild variant="outline">
            <Link to="/app/architecture" onClick={onClose} className="gap-2 text-xs sm:text-sm font-medium">
              <span>{t("pages.landing.featureModalArch")}</span>
              <ExternalLink className="size-3.5" aria-hidden="true" />
            </Link>
          </Button>

          <div className="flex items-center gap-2.5">
            <Button variant="ghost" onClick={onClose} className="text-xs sm:text-sm">
              {t("pages.landing.featureModalClose")}
            </Button>
            <Button asChild>
              <Link to="/app" onClick={onClose} className="gap-2 text-xs sm:text-sm font-medium">
                <span>{t("pages.landing.featureModalEnter")}</span>
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
