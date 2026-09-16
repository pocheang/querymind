import { useEffect, useReducer } from "react";

import { initialExecutionTraceState, reduceExecutionTrace } from "./state";
import { streamExecutionEvents } from "@/services/execution/execution-api";

export function useExecutionTrace(executionId: string | null) {
  const [state, dispatch] = useReducer(reduceExecutionTrace, initialExecutionTraceState);

  useEffect(() => {
    // Reset on EVERY change of id, not only on the null one run passes
    // through on its way to the next. `ask()` calls onExecutionId(null) and
    // then onExecutionId(<new uuid>) with only a microtask between them --
    // the id is client-generated now, so there is no network round trip in
    // between to force a render. React coalesces the pair, the `null` frame
    // is never rendered, and a reset keyed on it never runs. Measured, the
    // renders went straight from one id to the next carrying the previous
    // run's draft: `[{id:"run-a",draft:"run A answer"},{id:"run-b",draft:"run
    // A answer"}]`. That leaked the previous answer into the next bubble, the
    // previous reasoning into ThinkingPanel, and -- because the old
    // `complete` event was still in `events` -- made `isRunFinished` true at
    // once, so GenerationStatusLine never appeared again after the first
    // question. Resetting on any id change does not depend on which frames
    // React chooses to render.
    dispatch({ type: "execution_started" });
    if (!executionId) return;

    // Start streaming when we have an executionId
    const controller = new AbortController();
    void streamExecutionEvents(
      executionId,
      controller.signal,
      (event) => dispatch({ type: "event_received", event }),
      (text) => dispatch({ type: "answer_fragment", text }),
      (text) => dispatch({ type: "thought_fragment", text })
    );
    return () => controller.abort();
  }, [executionId]);

  return state;
}
