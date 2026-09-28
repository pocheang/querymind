import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { useAnswerShapeLabel } from "@/pages/chat/answerLabels";
import { useAgentClassName } from "@/pages/chat/agentModeLabels";

import type { RetrievalSourceOutcome, SessionMessageMetadata } from "@/types/api";

type Props = {
  metadata: SessionMessageMetadata;
};

function formatLatency(ms?: number) {
  const value = Number(ms || 0);
  if (!Number.isFinite(value) || value <= 0) return "";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

/**
 * Which sources actually produced evidence for this answer.
 *
 * This used to be one chip, `web: yes/no`, reading a field that no endpoint set
 * -- so it said "no" on every answer, including the ones written entirely from
 * web results. One boolean was the wrong shape anyway: the pipeline searches up
 * to eight sources and knows what each returned.
 *
 * A source that ran and found nothing is worth showing (it explains a thin
 * answer); one skipped because the caller has no documents is not a fact about
 * this answer and stays out.
 */
function sourceChips(metadata: SessionMessageMetadata) {
  const outcomes: RetrievalSourceOutcome[] = metadata.sources ?? [];
  if (outcomes.length === 0) {
    // Older messages, persisted before the metadata carried source outcomes.
    return metadata.web_used ? [{ source: "web", status: "completed", count: 1 }] : [];
  }
  return outcomes.filter((outcome) => outcome.status === "completed");
}

/**
 * "Cybersecurity · Exposure assessment": who answered, and in what shape.
 *
 * Named from the same labels the mode cards use, so a specialist is called the
 * same thing in the sidebar and on its answers. It used to print the raw class,
 * `agent: cybersecurity`, and only on re-run answers -- the chat response did
 * not carry the class at all. The general analyst answering in the default
 * shape is the unremarkable case and gets no badge.
 */
function useSpecialistBadge(metadata: SessionMessageMetadata): string {
  const className = useAgentClassName();
  const shapeLabel = useAnswerShapeLabel();
  const agentClass = metadata.agent_class || "";
  const skill = metadata.skill || "";
  if (!agentClass && !skill) return "";
  if (agentClass === "general" && (!skill || skill === "answer_with_citations")) return "";
  const who = className(agentClass);
  const shape = skill ? shapeLabel(skill) : "";
  return [who, shape].filter(Boolean).join(" · ");
}

export function MetadataBadges({ metadata }: Readonly<Props>) {
  const { t } = useTranslation();
  const specialist = useSpecialistBadge(metadata);
  const latency = formatLatency(metadata.latency_ms);
  const sources = sourceChips(metadata);

  return (
    <div className="flex flex-wrap items-center gap-1">
      {metadata.route && (
        <Badge variant="neutral" mono>
          route: {metadata.route}
        </Badge>
      )}
      {metadata.execution_route && (
        <Badge variant="neutral" mono>
          exec: {metadata.execution_route}
        </Badge>
      )}
      {metadata.route === "smalltalk_fast" && <Badge variant="info">smalltalk-fast</Badge>}
      {specialist && <Badge variant="info">{specialist}</Badge>}
      {sources.length === 0 ? (
        <Badge variant="outline">{t("chat.badges.noSources")}</Badge>
      ) : (
        sources.map((outcome) => (
          <Badge
            key={outcome.source}
            variant={outcome.count > 0 ? "success" : "outline"}
            mono
            title={t("chat.badges.sourceDetail", { source: outcome.source, count: outcome.count })}
          >
            {outcome.source}
            {outcome.count > 0 ? ` ${outcome.count}` : ""}
          </Badge>
        ))
      )}
      {latency && (
        <Badge variant="brand" mono>
          {latency}
        </Badge>
      )}
      {metadata.current_status && <Badge variant="neutral">{metadata.current_status}</Badge>}
      {(metadata.graph_entities || []).slice(0, 6).map((entity) => (
        <Badge key={entity} variant="brand" mono>
          {entity}
        </Badge>
      ))}
    </div>
  );
}
