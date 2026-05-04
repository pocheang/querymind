import { mapRunStatus } from "@/pages/chat/constants";

export interface ExecutionStep {
  kind: string;
  label: string;
  detail?: string;
  at?: string;
}

export interface StreamMetadata {
  current_status: string;
  execution_steps: ExecutionStep[];
  route?: string;
  execution_route?: string;
  retrieval_strategy?: string;
  agent_class?: string;
  web_used?: boolean;
  latency_ms?: number;
  thoughts?: string[];
  graph_entities?: any[];
  graph_result?: {
    entities: any[];
    neighbors: any[];
    paths: any[];
    context: string;
  };
  citations?: any[];
}

export interface StreamEventContext {
  answer: string;
  thoughts: string[];
  meta: StreamMetadata;
  executionSteps: ExecutionStep[];
  elapsedMs: () => number;
}

export interface StreamEventHandlers {
  handleStatusEvent: (evt: any, ctx: StreamEventContext) => { nextStatus: string; updatedCtx: StreamEventContext };
  handleRouteEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleThoughtEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleErrorEvent: (evt: any, ctx: StreamEventContext) => { error: Error; updatedCtx: StreamEventContext };
  handleVectorResultEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleGraphResultEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleWebResultEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleAnswerChunkEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleAnswerResetEvent: (evt: any, ctx: StreamEventContext) => StreamEventContext;
  handleDoneEvent: (evt: any, ctx: StreamEventContext, retrievalStrategy: string) => StreamEventContext;
}

function pushExecutionStep(
  ctx: StreamEventContext,
  kind: string,
  label: string,
  detail = ""
): StreamEventContext {
  const step: ExecutionStep = {
    kind,
    label,
    detail,
    at: new Date().toISOString(),
  };
  const updatedSteps = [...ctx.executionSteps, step].slice(-24);
  return {
    ...ctx,
    executionSteps: updatedSteps,
    meta: {
      ...ctx.meta,
      current_status: label,
      execution_steps: updatedSteps,
    },
  };
}

export function createStreamEventHandlers(): StreamEventHandlers {
  return {
    handleStatusEvent: (evt: any, ctx: StreamEventContext) => {
      const nextStatus = mapRunStatus(evt.message || "");
      const updatedCtx = nextStatus
        ? pushExecutionStep(ctx, "status", nextStatus, String(evt.message || ""))
        : ctx;
      return {
        nextStatus,
        updatedCtx: {
          ...updatedCtx,
          meta: {
            ...updatedCtx.meta,
            current_status: nextStatus,
          },
        },
      };
    },

    handleRouteEvent: (evt: any, ctx: StreamEventContext) => {
      const routeLabel = `路由完成: ${evt.route || "unknown"}`;
      const detail = [
        evt.reason,
        evt.skill ? `skill=${evt.skill}` : "",
        evt.agent_class ? `agent=${evt.agent_class}` : "",
      ]
        .filter(Boolean)
        .join(" | ");

      const updatedCtx = pushExecutionStep(ctx, "route", routeLabel, detail);
      return {
        ...updatedCtx,
        meta: {
          ...updatedCtx.meta,
          route: evt.route || "",
          agent_class: evt.agent_class || "",
          current_status: routeLabel,
        },
      };
    },

    handleThoughtEvent: (evt: any, ctx: StreamEventContext) => {
      if (!evt.content) return ctx;
      const updatedThoughts = [...ctx.thoughts, String(evt.content)];
      const updatedCtx = pushExecutionStep(ctx, "thought", "分析判断", String(evt.content));
      return {
        ...updatedCtx,
        thoughts: updatedThoughts,
      };
    },

    handleErrorEvent: (evt: any, ctx: StreamEventContext) => {
      const reason = String(evt.message || evt.error || "stream error");
      const cost = ctx.elapsedMs();
      const updatedCtx = pushExecutionStep(ctx, "error", "执行失败", `${reason} | duration_ms=${cost}`);
      return {
        error: new Error(reason),
        updatedCtx: {
          ...updatedCtx,
          meta: {
            ...updatedCtx.meta,
            current_status: "执行失败",
            latency_ms: cost,
          },
        },
      };
    },

    handleVectorResultEvent: (evt: any, ctx: StreamEventContext) => {
      const retrievedCount = Number(evt.retrieved_count || 0);
      const updatedCtx = pushExecutionStep(ctx, "vector", "向量检索完成", `命中片段 ${retrievedCount} 条`);
      return {
        ...updatedCtx,
        meta: {
          ...updatedCtx.meta,
          current_status: "向量检索完成",
        },
      };
    },

    handleGraphResultEvent: (evt: any, ctx: StreamEventContext) => {
      const entities = Array.isArray(evt.entities) ? evt.entities : [];
      const neighbors = Array.isArray(evt.neighbors) ? evt.neighbors : [];
      const paths = Array.isArray(evt.paths) ? evt.paths : [];
      const context = evt.context || "";

      const updatedCtx = pushExecutionStep(
        ctx,
        "graph",
        "图谱检索完成",
        `命中 ${entities.length} 个实体, ${neighbors.length} 个邻居关系, ${paths.length} 条路径`
      );

      return {
        ...updatedCtx,
        meta: {
          ...updatedCtx.meta,
          graph_entities: entities,
          graph_result: {
            entities,
            neighbors,
            paths,
            context,
          },
          current_status: "图谱检索完成",
        },
      };
    },

    handleWebResultEvent: (evt: any, ctx: StreamEventContext) => {
      const webLabel = !!evt.used ? "联网补充完成" : "未触发联网补充";
      const updatedCtx = pushExecutionStep(ctx, "web", webLabel, `web_used=${!!evt.used}`);
      return {
        ...updatedCtx,
        meta: {
          ...updatedCtx.meta,
          web_used: !!evt.used,
          current_status: webLabel,
        },
      };
    },

    handleAnswerChunkEvent: (evt: any, ctx: StreamEventContext) => {
      return {
        ...ctx,
        answer: ctx.answer + String(evt.content || ""),
      };
    },

    handleAnswerResetEvent: (evt: any, ctx: StreamEventContext) => {
      const updatedCtx = pushExecutionStep(ctx, "rewrite", "答案已校正", "系统对流式答案做了一次重写或修正");
      return {
        ...updatedCtx,
        answer: String(evt.content || ""),
        meta: {
          ...updatedCtx.meta,
          current_status: "答案已校正",
        },
      };
    },

    handleDoneEvent: (evt: any, ctx: StreamEventContext, retrievalStrategy: string) => {
      const result = evt.result || {};
      const finalAnswer = String(result.answer || ctx.answer || "");
      const cost = ctx.elapsedMs();

      const detail = [
        result.route ? `route=${result.route}` : "",
        result.agent_class ? `agent=${result.agent_class}` : "",
        result.web_result ? `web=${!!result.web_result.used}` : "",
        `duration_ms=${cost}`,
      ]
        .filter(Boolean)
        .join(" | ");

      const updatedCtx = pushExecutionStep(ctx, "done", "执行完成", detail);

      return {
        ...updatedCtx,
        answer: finalAnswer,
        meta: {
          ...updatedCtx.meta,
          route: result.route || ctx.meta.route,
          execution_route: result.execution_route || result.debug?.execution_route || ctx.meta.execution_route,
          retrieval_strategy: result.retrieval_strategy || result.debug?.retrieval_strategy || retrievalStrategy,
          agent_class: result.agent_class || ctx.meta.agent_class,
          web_used: !!(result.web_result && result.web_result.used),
          latency_ms: cost,
          thoughts: Array.isArray(result.thoughts) ? result.thoughts : ctx.thoughts,
          graph_entities: (result.graph_result && result.graph_result.entities) || ctx.meta.graph_entities || [],
          current_status: "执行完成",
          citations: [
            ...(((result.vector_result && result.vector_result.citations) || []) as any[]),
            ...(((result.web_result && result.web_result.citations) || []) as any[]),
          ],
        },
      };
    },
  };
}
