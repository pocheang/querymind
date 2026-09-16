import { isExecutionEvent, type ExecutionEvent } from "./types";

export type { ExecutionEvent } from "./types";

export type ExecutionTraceState = {
  events: readonly ExecutionEvent[];
  /** The answer as it is being written. Server-side redacted, but a *draft*:
   *  no citation numbering and no reference list, both of which are decided
   *  once the whole answer exists. Replaced by the final answer on completion. */
  draft: string;
  /** The model's reasoning as it is being written, only ever non-empty when
   *  the request opted in to visible reasoning (`use_reasoning`). Same draft
   *  caveat as `draft`: server-side redacted, but not yet the persisted,
   *  final-redaction-pass copy that arrives with the query response. */
  thinking: string;
};

export const initialExecutionTraceState: ExecutionTraceState = { events: [], draft: "", thinking: "" };

export type ExecutionTraceAction =
  | { type: "execution_started" }
  | { type: "event_received"; event: unknown }
  | { type: "answer_fragment"; text: string }
  | { type: "thought_fragment"; text: string };

export function reduceExecutionTrace(state: ExecutionTraceState, action: ExecutionTraceAction): ExecutionTraceState {
  if (action.type === "execution_started") return initialExecutionTraceState;
  if (action.type === "answer_fragment") return { ...state, draft: state.draft + action.text };
  if (action.type === "thought_fragment") return { ...state, thinking: state.thinking + action.text };
  if (!isExecutionEvent(action.event)) return state;
  return { ...state, events: [...state.events, action.event] };
}
