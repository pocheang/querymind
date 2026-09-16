// @vitest-environment jsdom
import { act, render } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * One run's trace must never bleed into the next.
 *
 * The reset used to be keyed on `executionId` becoming null, which worked
 * only because the id arrived with the query RESPONSE: `ask()` set null, a
 * real network round trip forced a render, and the new id came after. Once
 * the client generates the id itself and publishes it BEFORE sending the
 * request, those two updates are separated by a microtask and nothing else,
 * React coalesces them, and the `null` frame is never rendered -- so the
 * reset never ran. Measured on the shipped code, the renders went
 * `{id:"run-a",draft:"run A answer"}` -> `{id:"run-b",draft:"run A answer"}`.
 *
 * Four things leaked with it: the previous answer into the next streaming
 * bubble, the previous reasoning into ThinkingPanel, the previous events into
 * the trace panel, and -- because the old `complete` event was still in
 * `events` -- `isRunFinished` was true from the first render of the new run,
 * so `GenerationStatusLine` never appeared again after the first question.
 */

type Emit = {
  event?: (event: unknown) => void;
  answer?: (text: string) => void;
  thought?: (text: string) => void;
};
let emit: Emit = {};

vi.mock("@/services/execution/execution-api", () => ({
  streamExecutionEvents: async (
    _executionId: string,
    _signal: AbortSignal,
    onEvent: (event: unknown) => void,
    onAnswerFragment?: (text: string) => void,
    onThoughtFragment?: (text: string) => void
  ) => {
    emit = { event: onEvent, answer: onAnswerFragment, thought: onThoughtFragment };
    // Never resolves: a live subscription, ended by the effect's abort.
    await new Promise(() => {});
  },
}));

const { useExecutionTrace } = await import("./useExecutionTrace");

const completeEvent = {
  version: "1",
  stage: "complete",
  status: "completed",
  duration_ms: 1,
  message: "",
  metadata: [],
  occurred_at: "2026-09-15T00:00:00Z",
};

let seen = { draft: "", thinking: "", events: 0 };
let setId: ((value: string | null) => void) | null = null;

function Probe() {
  const [id, set] = useState<string | null>("run-a");
  setId = set;
  const trace = useExecutionTrace(id);
  seen = { draft: trace.draft, thinking: trace.thinking, events: trace.events.length };
  return null;
}

/** A first run that got as far as a finished answer, reasoning and a
 *  terminal event -- everything that must not survive into the next one. */
async function renderAfterOneFinishedRun() {
  render(<Probe />);
  await act(async () => {});
  await act(async () => {
    emit.answer?.("run A answer");
    emit.thought?.("run A reasoning");
    emit.event?.(completeEvent);
  });
  expect(seen).toEqual({ draft: "run A answer", thinking: "run A reasoning", events: 1 });
}

afterEach(() => {
  emit = {};
  seen = { draft: "", thinking: "", events: 0 };
  setId = null;
});

describe("useExecutionTrace across runs", () => {
  it("clears draft, reasoning and events when the execution id changes directly", async () => {
    await renderAfterOneFinishedRun();

    await act(async () => setId?.("run-b"));

    expect(seen).toEqual({ draft: "", thinking: "", events: 0 });
  });

  it("clears them when null and the next id land in one render, as ask() produces", async () => {
    // Both updates inside one act() flush: exactly the coalescing the real
    // `ask()` gets from setting null and then the new uuid a microtask apart.
    // The component therefore never renders with `executionId === null`,
    // which is what the old reset depended on.
    await renderAfterOneFinishedRun();

    await act(async () => {
      setId?.(null);
      await Promise.resolve();
      setId?.("run-b");
    });

    expect(seen).toEqual({ draft: "", thinking: "", events: 0 });
  });

  it("still accumulates within one run", async () => {
    render(<Probe />);
    await act(async () => {});

    await act(async () => {
      emit.answer?.("Retrieval");
      emit.thought?.("Step 1: ");
    });
    await act(async () => {
      emit.answer?.(" augmented");
      emit.thought?.("analyze.");
    });

    expect(seen).toEqual({ draft: "Retrieval augmented", thinking: "Step 1: analyze.", events: 0 });
  });
});
