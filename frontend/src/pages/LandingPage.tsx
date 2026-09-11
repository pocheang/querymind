import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  FeatureDetailModal,
  LandingAgentsSection,
  LandingArchitectureSection,
  LandingCtaAndFooter,
  LandingFeaturesSection,
  LandingHeader,
  LandingHeroSection,
  LandingWorkflowSection,
  type FeatureItem,
} from "./landing";

interface LandingPageProps {
  isLoggedIn: boolean;
}

export function LandingPage({ isLoggedIn }: Readonly<LandingPageProps>) {
  const { t, i18n } = useTranslation();
  const [activeFeature, setActiveFeature] = useState<FeatureItem | null>(null);

  useEffect(() => {
    document.title = `${t("app.title")} - ${t("app.subtitle")}`;
  }, [i18n.language, t]);

  return (
    <div className="landing-root aurora-bg min-h-screen">
      <LandingHeader isLoggedIn={isLoggedIn} />
      <LandingHeroSection isLoggedIn={isLoggedIn} />
      <LandingFeaturesSection onSelectFeature={setActiveFeature} />
      <LandingAgentsSection />
      <LandingWorkflowSection />
      <LandingArchitectureSection />
      <LandingCtaAndFooter isLoggedIn={isLoggedIn} />

      <FeatureDetailModal
        feature={activeFeature}
        isOpen={activeFeature !== null}
        onClose={() => setActiveFeature(null)}
      />
    </div>
  );
}
