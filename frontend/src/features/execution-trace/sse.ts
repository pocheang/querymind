import { isExecutionEvent as isExecutionEventType, type ExecutionEvent } from "./types";

export { isExecutionEvent } from "./types";
export type { ExecutionEvent } from "./types";

const SSE_EVENT_NAME = "event: execution_event";
const SSE_ANSWER_NAME = "event: answer_fragment";
const SSE_THOUGHT_NAME = "event: thought_fragment";

export function parseExecutionEventSse(frame: string): ExecutionEvent | null {
  const lines = frame.split("\n");
  if (!lines.includes(SSE_EVENT_NAME)) return null;
  const data = lines.find((line) => line.startsWith("data: "));
  if (!data) return null;
  try {
    const value: unknown = JSON.parse(data.slice("data: ".length));
    return isExecutionEventType(value) ? value : null;
  } catch {
    return null;
  }
}

/** A redacted draft fragment. Carries no citation numbering and no reference
 *  list: those are decided server-side once the whole answer exists, and arrive
 *  with the final response. */
export function parseAnswerFragmentSse(frame: string): string | null {
  return parseFragmentSse(frame, SSE_ANSWER_NAME);
}

/** A redacted reasoning-draft fragment. Only ever sent when the request opted
 *  in to visible reasoning (`use_reasoning`); an execution that did not asks
 *  simply never receives this event. Same wire shape as `answer_fragment`,
 *  under its own event name so a client cannot mistake one for the other. */
export function parseThoughtFragmentSse(frame: string): string | null {
  return parseFragmentSse(frame, SSE_THOUGHT_NAME);
}

function parseFragmentSse(frame: string, eventName: string): string | null {
  const lines = frame.split("\n");
  if (!lines.includes(eventName)) return null;
  const data = lines.find((line) => line.startsWith("data: "));
  if (!data) return null;
  try {
    const value: unknown = JSON.parse(data.slice("data: ".length));
    if (typeof value !== "object" || value === null) return null;
    const text = (value as Record<string, unknown>).text;
    return typeof text === "string" ? text : null;
  } catch {
    return null;
  }
}

export async function consumeExecutionEventStream(
  response: Response,
  onEvent: (event: ExecutionEvent) => void,
  signal: AbortSignal,
  onAnswerFragment?: (text: string) => void,
  onThoughtFragment?: (text: string) => void
): Promise<void> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (!signal.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const event = parseExecutionEventSse(frame);
        if (event) {
          onEvent(event);
          continue;
        }
        const fragment = parseAnswerFragmentSse(frame);
        if (fragment !== null) {
          onAnswerFragment?.(fragment);
          continue;
        }
        const thought = parseThoughtFragmentSse(frame);
        if (thought !== null) onThoughtFragment?.(thought);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
