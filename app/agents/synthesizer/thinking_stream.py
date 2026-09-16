"""Split a live model token stream into reasoning and answer channels.

`COT_VISIBLE_REASONING_PROMPT` (app/agents/synthesizer/templates.py) asks the
model to open with a ``<think>...</think>`` block, only when the caller opted
in to seeing reasoning. `ReasoningStreamSplitter` finds that boundary in real
time, across however many chunks the tag happens to be split into by the
model's own tokenization -- the same chunk-boundary-safety concern
`StreamingRedactor` (app/privacy/streaming.py) already solves for redaction,
applied here to a delimiter instead of a secret pattern.

This only decides *which channel* a piece of text belongs to. Neither channel
is redacted here -- the caller pushes each piece through its own
`StreamingRedactor` afterward, exactly as the single answer channel already
does.
"""

from __future__ import annotations

from dataclasses import dataclass

Channel = str  # "thought" | "answer"

_OPEN_TAG = "<think>"
_CLOSE_TAG = "</think>"

# How many characters of a plain answer are given the benefit of the doubt
# before concluding the model did not open a reasoning block this time.
# Generous enough for a stray leading newline or a short "Sure,"; small enough
# that a real answer is never held back for long waiting on a tag that is not
# coming.
_SNIFF_LIMIT = 40


@dataclass
class ReasoningStreamSplitter:
    """Feed raw model chunks in; get back ``(channel, text)`` pairs to publish.

    Three states: ``before`` (sniffing for the opening tag), ``thinking``
    (inside the block), ``after`` (past it -- the fast path once resolved, no
    more buffering needed). A model that never opens the tag resolves to
    ``after`` once `_SNIFF_LIMIT` characters have accumulated with no match,
    and everything buffered flushes as ``answer`` -- a non-compliant model
    still produces a normal answer, it just never gets a reasoning panel.
    """

    _state: str = "before"
    _buffer: str = ""

    def feed(self, chunk: str) -> list[tuple[Channel, str]]:
        if not chunk:
            return []
        if self._state == "after":
            return [("answer", chunk)]

        self._buffer += chunk
        out: list[tuple[Channel, str]] = []

        if self._state == "before":
            idx = self._buffer.find(_OPEN_TAG)
            if idx == -1:
                if len(self._buffer) >= _SNIFF_LIMIT:
                    out.append(("answer", self._buffer))
                    self._buffer = ""
                    self._state = "after"
                return out
            leading = self._buffer[:idx]
            if leading:
                out.append(("answer", leading))
            self._buffer = self._buffer[idx + len(_OPEN_TAG) :]
            self._state = "thinking"

        if self._state == "thinking":
            idx = self._buffer.find(_CLOSE_TAG)
            if idx == -1:
                # Hold back enough characters that a `</think>` split across
                # this chunk and the next can never be emitted as thought text.
                margin = len(_CLOSE_TAG) - 1
                if len(self._buffer) > margin:
                    releasable = self._buffer[: len(self._buffer) - margin]
                    if releasable:
                        out.append(("thought", releasable))
                    self._buffer = self._buffer[len(self._buffer) - margin :]
                return out
            thought = self._buffer[:idx]
            if thought:
                out.append(("thought", thought))
            trailing = self._buffer[idx + len(_CLOSE_TAG) :]
            self._buffer = ""
            self._state = "after"
            if trailing:
                out.append(("answer", trailing))

        return out

    def finish(self) -> list[tuple[Channel, str]]:
        """Flush whatever is left -- nothing more is coming.

        Only reachable with leftover text in two ordinary cases (a short
        answer under the sniff limit; a held-back `</think>` margin) and one
        malformed one (`<think>` opened but never closed -- truncated
        generation). The malformed case flushes as `thought`, since that is
        where the buffered text logically belongs; `extract_reasoning_block`
        (app/agents/synthesizer/citations.py) makes the same call
        independently on the complete non-streaming text.
        """
        if not self._buffer:
            return []
        channel: Channel = "thought" if self._state == "thinking" else "answer"
        out = [(channel, self._buffer)]
        self._buffer = ""
        return out


__all__ = ["ReasoningStreamSplitter"]
