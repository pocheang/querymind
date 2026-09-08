import { useTranslation } from "react-i18next";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { SessionMessageMetadata } from "@/types/api";

type GraphResult = NonNullable<SessionMessageMetadata["graph_result"]>;
type GraphPath = GraphResult["paths"][number];

/**
 * Knowledge-graph neighbours and paths for one answer.
 *
 * Extracted from `MessageCard`, where ~90 lines of shape-sniffing over two
 * historical path formats sat inline in the JSX. The two formats are real --
 * `entities`/`relations` is what the graph route emits now, `source`/`middle`/
 * `target` is what older stored messages carry -- so both are still read here,
 * just somewhere a reader can see the whole decision at once.
 */
export function MessageGraphPanel({ graph, keyPrefix }: Readonly<{ graph: GraphResult; keyPrefix: string }>) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3">
      {graph.neighbors.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
            {t("components.messages.neighbors", { count: graph.neighbors.length })}
          </p>
          <div className="space-y-1">
            {graph.neighbors.slice(0, 10).map((neighbor, index) => (
              <div
                key={`${keyPrefix}-neighbor-${index}`}
                className="flex flex-wrap items-center gap-1.5 rounded-control border border-line bg-surface px-2 py-1 font-mono text-[10px]"
              >
                <span className="font-semibold text-ink">{neighbor.entity}</span>
                {neighbor.direction === "out" ? (
                  <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
                ) : (
                  <ArrowLeft className="size-3 text-brand-accent" aria-hidden="true" />
                )}
                <Badge variant="brand" size="xs" mono>
                  {neighbor.relation}
                </Badge>
                <span className="text-ink-muted">{t("components.messages.targetEntity")}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {graph.paths.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
            {t("components.messages.paths", { count: graph.paths.length })}
          </p>
          <div className="space-y-1">
            {graph.paths.slice(0, 5).map((path, index) => (
              <GraphPathRow key={`${keyPrefix}-path-${index}`} path={path} />
            ))}
          </div>
        </div>
      )}

      {graph.context && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
            {t("components.messages.graphContext")}
          </p>
          <pre className="max-h-48 overflow-auto rounded-control border border-line bg-surface p-2 font-mono text-[10px] text-ink select-text">
            {graph.context}
          </pre>
        </div>
      )}
    </div>
  );
}

function GraphPathRow({ path }: Readonly<{ path: GraphPath }>) {
  const { t } = useTranslation();
  const row =
    "flex flex-wrap items-center gap-1 rounded-control border border-line bg-surface px-2 py-1 font-mono text-[10px]";

  if ("entities" in path && Array.isArray(path.entities)) {
    return (
      <div className={row}>
        {path.entities.map((entity, entityIndex) => (
          <span key={`${entity}-${entityIndex}`} className="flex items-center gap-1">
            <span className="font-semibold text-ink">{entity}</span>
            {entityIndex < (path.relations?.length || 0) && (
              <>
                <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
                <Badge variant="brand" size="xs" mono>
                  {path.relations[entityIndex]}
                </Badge>
                <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
              </>
            )}
          </span>
        ))}
      </div>
    );
  }

  if ("source" in path && "middle" in path && "target" in path) {
    return (
      <div className={row}>
        <span className="font-semibold text-ink">{path.source}</span>
        <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
        <Badge variant="brand" size="xs" mono>
          {path.rel1 || "RELATED"}
        </Badge>
        <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
        <span className="font-semibold text-ink">{path.middle}</span>
        <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
        <Badge variant="brand" size="xs" mono>
          {path.rel2 || "RELATED"}
        </Badge>
        <ArrowRight className="size-3 text-brand-accent" aria-hidden="true" />
        <span className="font-semibold text-ink">{path.target}</span>
      </div>
    );
  }

  return (
    <div className={row}>
      <span className="text-danger">{t("components.messages.pathIncomplete")}</span>
    </div>
  );
}
