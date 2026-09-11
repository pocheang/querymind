import type { ComponentType } from "react";
import type { FeatureItem } from "./FeatureDetailModal";

export type { FeatureItem };

export interface SectionHeadingProps {
  lead: string;
  accent: string;
  sub: string;
}

export interface FeatureCategory {
  key: string;
  label: string;
}

export interface WorkflowStep {
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  title: string;
  body: string;
  tag: string;
}

export interface TrustMetric {
  value: string;
  label: string;
  desc: string;
}

export interface AgentCard {
  key: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  title: string;
  desc: string;
  badge: string;
  featured: boolean;
  accent: string;
  capabilities: string[];
  link: string;
  actionText: string;
}
