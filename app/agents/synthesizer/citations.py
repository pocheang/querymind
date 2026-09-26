"""Citation-label extraction, answer normalization, and reference numbering.

Two marker formats live here and they are not interchangeable.  ``[E1]`` is the
*internal* evidence marker: it is what ``ContextBuilder`` renders in front of
each excerpt, what the prompts teach, and what ``normalize_answer_citations``
allow-lists, so it always names an exact position in the evidence list.
``[1]`` is the *reader-facing* marker produced at the very end of the run by
``number_evidence_markers``, numbered by first appearance the way a paper's
reference list is.  Nothing between synthesis and the output filter should have
to know about the second form.

``[T1]`` marks a fact taken from a governed tool result. It has its own label
space on purpose: a tool result is not evidence -- it is not a retrieved
document, carries no document id and is never masked as one -- so it must not
borrow an ``[E{k}]`` number, and ``citation_labels_from_contexts`` is never
given the tool section. The output filter renumbers ``[T{k}]`` by first
appearance, like ``[E{k}]``, and lists the tools under their own heading.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from pathlib import Path

from app.domain.contracts import EvidenceItem, ToolResult

_CITATION_LABEL_PATTERN = r"[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?"
_EVIDENCE_RECORD_RE = re.compile(rf"(?m)^\s*\[({_CITATION_LABEL_PATTERN})\][ \t]+\S")
_CITATION_LABEL_RE = re.compile(rf"^{_CITATION_LABEL_PATTERN}$")
_BRACKETED_MARKER_RE = re.compile(r"\[([^\]\r\n]+)\](?!\()")

EVIDENCE_MARKER_RE = re.compile(r"\[E(\d+)\]")
"""The one place the internal evidence-marker shape is defined."""

TOOL_MARKER_RE = re.compile(r"\[T(\d+)\]")
"""The one place the tool-result marker shape is defined."""

# A tool record in the prompt's tool section: `[T1] (tool_id) ...` at the
# start of a line. Only the tool section is ever scanned with this.
_TOOL_RECORD_RE = re.compile(r"(?m)^\[(T\d+)\][ \t]")

_REFERENCE_HEADINGS = {"zh": "参考来源", "en": "References"}
_TOOL_SOURCE_HEADINGS = {"zh": "工具来源", "en": "Tool sources"}
_TOOL_SOURCE_SUMMARY_CHARS = 160

# A whole run of spaces, plus the punctuation after it when there is one. The
# optional group means a match cannot fail once it has started.
_SPACE_RUN_RE = re.compile(r"[ \t]+([,.;:!?]?)")


def _drop_space_before_punctuation(match: re.Match[str]) -> str:
    return match.group(1) or match.group(0)


def citation_labels_from_contexts(*contexts: str) -> frozenset[str]:
    """Return labels from leading ``[label] content`` evidence records."""
    return frozenset(
        label.strip() for context in contexts for label in _EVIDENCE_RECORD_RE.findall(context or "") if label.strip()
    )


def citable_tool_results(tool_results: Sequence[ToolResult]) -> tuple[ToolResult, ...]:
    """The tool results an answer may cite, in ``[T1]``, ``[T2]``, ... order.

    Only a tool that ran and said something: a failure or a pending approval
    reports that an action did NOT happen, which is worth telling the reader
    and is not a fact to attribute. A ``derived`` result -- a specialist's
    regex over material the model already has -- is never citable: a citation
    pointing at a derivation instead of a source is the thing
    ``BaseSpecialistAgent.domain_findings`` exists to prevent.

    The synthesizer numbers the prompt with this and the output filter
    resolves markers with it, over the same tuple, so ``[T{k}]`` names the
    same result at both ends.
    """

    return tuple(
        result
        for result in tool_results
        if result.status == "succeeded" and result.summary.strip() and not result.derived
    )


def tool_citation_labels(tool_context: str) -> frozenset[str]:
    """The ``T{k}`` labels the prompt's tool section offers."""

    return frozenset(_TOOL_RECORD_RE.findall(tool_context or ""))


def number_tool_markers(text: str, citable: Sequence[ToolResult]) -> tuple[str, tuple[ToolResult, ...]]:
    """Rewrite ``[T{k}]`` by first appearance, dropping any that resolve to nothing.

    The same rule ``number_evidence_markers`` applies to ``[E{k}]``: numbered
    in reading order, and a marker past the end of the list removed rather
    than left pointing at no entry. The same tool cited twice keeps one number.
    """

    cited: list[ToolResult] = []
    numbers: dict[int, int] = {}

    def renumber(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index < 1 or index > len(citable):
            return ""
        number = numbers.get(index)
        if number is None:
            number = len(cited) + 1
            numbers[index] = number
            cited.append(citable[index - 1])
        return f"[T{number}]"

    return _tidy_spacing(TOOL_MARKER_RE.sub(renumber, str(text or ""))), tuple(cited)


def render_tool_source_list(cited: Sequence[ToolResult], language: str = "zh") -> str:
    """The tool sources section, appended after the reference list.

    Each line names the tool and the first line of what it returned, so a
    reader can see where a number came from without opening the tool panel.
    The caller runs output DLP over the result: the summary is tool output.
    """

    if not cited:
        return ""
    heading = _TOOL_SOURCE_HEADINGS.get(language, _TOOL_SOURCE_HEADINGS["zh"])
    lines = [f"**{heading}**", ""]
    for number, result in enumerate(cited, start=1):
        first_line = result.summary.strip().splitlines()[0].strip()
        if len(first_line) > _TOOL_SOURCE_SUMMARY_CHARS:
            first_line = first_line[: _TOOL_SOURCE_SUMMARY_CHARS - 1].rstrip() + "…"
        lines.append(f"- [T{number}] {result.tool_id}: {first_line}")
    return "\n".join(lines)


def normalize_answer_citations(text: str, allowed_labels: Collection[str]) -> str:
    """Preserve allowed citations and remove non-allowlisted citation markers."""
    allowed = frozenset(str(label).strip() for label in allowed_labels if str(label).strip())

    def replace_marker(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        if label in allowed or not _CITATION_LABEL_RE.fullmatch(label):
            return match.group(0)
        return ""

    return _tidy_spacing(_BRACKETED_MARKER_RE.sub(replace_marker, str(text or "")))


def number_evidence_markers(
    text: str,
    evidence: Sequence[EvidenceItem],
    *,
    keep_item_ids: Collection[str] | None = None,
) -> tuple[str, tuple[EvidenceItem, ...]]:
    """Rewrite internal ``[E{k}]`` markers as reader-facing ``[1]``, ``[2]``, ...

    Numbers are assigned in order of *first appearance in the answer*, not in
    retrieval order, so the returned reference list reads top-down the way a
    paper's does and never has gaps for evidence the model did not cite.

    Two excerpts a reader would see as the same source -- same ``source`` and
    same ``page`` -- share one number, because rendering ``[1]`` and ``[2]`` as
    two identical reference lines reads as a bug.  The first of them becomes the
    reference entry.

    ``keep_item_ids`` is the set that survived output filtering.  A marker
    pointing at anything else, or past the end of the evidence list, is removed
    rather than left dangling: a ``[n]`` with no entry to resolve to is worse
    than no citation at all.

    Returns the rewritten text and the reference items in numbered order, so
    ``references[n - 1]`` is what ``[n]`` in the text points at.
    """

    references: list[EvidenceItem] = []
    numbers: dict[tuple[str, int | None], int] = {}
    allowed = None if keep_item_ids is None else frozenset(keep_item_ids)

    def renumber(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if index < 1 or index > len(evidence):
            return ""
        item = evidence[index - 1]
        if allowed is not None and item.item_id not in allowed:
            return ""
        key = _reference_key(item)
        number = numbers.get(key)
        if number is None:
            number = len(references) + 1
            numbers[key] = number
            references.append(item)
        return f"[{number}]"

    return _tidy_spacing(EVIDENCE_MARKER_RE.sub(renumber, str(text or ""))), tuple(references)


def reference_label(item: EvidenceItem, language: str = "zh") -> str:
    """Name one source the way a reader identifies it, not the way the store does.

    Local evidence is shown by filename: ``item.source`` is a storage path, and
    the directory part identifies the tenant layout rather than the document.
    Web evidence keeps its full URL, which is the only thing that identifies it.
    """

    source = str(item.source or "").strip()
    if source.startswith(("http://", "https://")):
        name = source
    else:
        name = Path(source).name or source
    if item.page is None:
        return name
    return f"{name} · 第 {item.page} 页" if language == "zh" else f"{name} · p. {item.page}"


# A reference heading the model may have written for itself: bolded, hash-headed
# or bare, in either language. Anchored to the start of a line, so a sentence
# that merely mentions the word is untouched.
_MODEL_REFERENCE_BLOCK_RE = re.compile(
    r"\n{0,2}[ \t]{0,8}(?:\*\*|#{1,4}[ \t]{0,4})?"
    r"(?:" + "|".join(re.escape(h) for h in _REFERENCE_HEADINGS.values()) + r")"
    r"(?:\*\*)?[ \t]{0,8}[:：]?[ \t]{0,8}\n+"
    r"(?:[ \t]{0,8}(?:[-*][ \t]{0,4})?\[[^\]\r\n]{1,120}\][^\n]{0,400}\n{0,2}){1,40}\s*$"
)


def strip_model_reference_list(text: str) -> str:
    """Remove a reference section the MODEL wrote at the end of its answer.

    `output_filter` appends the authoritative list -- it is the only thing that
    knows which citations survived DLP and what number each evidence item got --
    so a section the model wrote for itself is redundant by construction. When
    both are present the reader gets the same heading twice, and the model's
    copy carries whatever it was shown. A real answer on 2026-09-09 ended with

        参考来源

        [1] <URL_7>

        **参考来源**

        - [1] https://arxiv.org/html/2602.20924v1

    where `<URL_7>` is the outbound-redaction token. That token is restored in
    the model wrapper now; the duplicate heading is a separate defect and this
    is where it belongs.

    Deliberately conservative: matched only at the END of the answer, only when
    every line after the heading is a bracketed entry, and bounded to forty of
    them. A model that wrote prose under that heading keeps it -- losing an
    answer's last paragraph to a tidy-up is far worse than one repeated heading.
    """

    return _MODEL_REFERENCE_BLOCK_RE.sub("", str(text or "")).rstrip()


# The two step names most likely to survive verbatim if a model echoes
# `COT_REASONING_PROMPT` (app/agents/synthesizer/templates.py) back into its
# reply: they are copied from the prompt's own numbered list, where a
# self-chosen heading like "Chain-of-Thought Analysis" is the model's own
# wording and cannot be relied on to match.
_COT_SIGNAL_PHRASES = ("Query Analysis", "Answer Structure")
_COT_ANSWER_MARKERS = ("answer", "答案")


def strip_chain_of_thought_preamble(text: str) -> str:
    """Remove a chain-of-thought scaffold the MODEL wrote ahead of its answer.

    `COT_REASONING_PROMPT` asks the model to "think through" four numbered
    steps -- Query Analysis, Context Assessment, Citation Planning, Answer
    Structure -- before answering, the way a real reasoning model keeps its
    scratch work internal. Nothing in that prompt said the scratch work must
    stay out of the reply, and a model that takes "think through" at face
    value writes the whole thing out -- self-labelled "Chain-of-Thought
    Analysis" in one observed answer -- with the real answer starting only
    after a line that is just "Answer:". A reader then sees the machinery
    that produced the answer instead of the answer, which is the same
    failure this file already strips a model's own reference section for.

    Conservative like `strip_model_reference_list` beside it: this only acts
    once it has seen two of the prompt's own step names, and only cuts at an
    explicit "Answer:" line of its own. A response that never reaches one is
    left exactly as the model wrote it -- guessing a cut point would risk
    taking the only content the model produced.
    """

    raw = str(text or "")
    head = raw[:4000]
    if not all(phrase in head for phrase in _COT_SIGNAL_PHRASES):
        return raw

    lines = raw.split("\n")
    for index, line in enumerate(lines):
        marker = line.strip().strip("*").strip().rstrip(":：").strip().lower()
        if marker in _COT_ANSWER_MARKERS:
            return "\n".join(lines[index + 1 :]).lstrip()
    return raw


# `ANSWER_PROMPT` used to embed its own Chinese four-step "think before
# answering" block, a near-exact duplicate of `COT_REASONING_PROMPT`
# (app/agents/synthesizer/templates.py) sent alongside it in the same
# request -- one step of it, "what does the user really want to know", is
# answering exactly the question this catches a model narrating out loud.
# The duplicate is gone and both prompts now say the analysis must stay
# internal, but this stays as the safety net for whichever prompt a model
# still answers out of: a real, observed multi-turn follow-up (2026-09-15)
# opened its reply with
#
#     Based on the conversation history, the user is asking about the
#     limitations of BM25 in information retrieval.
#
#     Main Limitations of BM25:
#     ...
#
# -- a sentence about the model's own reading of the exchange, not part of
# the answer, and it survived because it names no fixed second marker like
# COT_REASONING_PROMPT's "Answer:" line to cut at. Unlike that stripper,
# this one only ever inspects the FIRST sentence and only removes exactly
# that sentence -- guessing a paragraph boundary risks taking real answer
# text that happens to follow without a blank line in between.
_CONVERSATION_META_HISTORY_TERMS = (
    "conversation history",
    "chat history",
    "previous conversation",
    "prior conversation",
    "对话历史",
    "历史对话",
    "之前的对话",
    "聊天记录",
)
_CONVERSATION_META_ASKING_TERMS = (
    "the user is asking",
    "user is asking",
    "user's question",
    "用户在问",
    "用户想问",
    "用户问的是",
    "用户的问题是",
    "用户询问",
)
# Chinese sentence-final punctuation needs no trailing space to end a
# sentence; ASCII punctuation does, so a decimal or an abbreviation inside
# the leaked sentence itself cannot end the match early.
_FIRST_SENTENCE_END_RE = re.compile(r"[。！？]|[.!?](?=\s|$)")


def strip_conversation_meta_preamble(text: str) -> str:
    """Remove a leading sentence where the MODEL narrates its own reading of
    the conversation, instead of just answering. See the module comment
    above for the observed case this pins.

    Conservative like `strip_chain_of_thought_preamble` beside it: only the
    text up to the first sentence terminator is inspected, and it is removed
    only once it mentions both the conversation/history AND a restatement of
    what the user is asking -- a real answer that happens to mention "the
    conversation" in passing, with no second signal, is left untouched.
    """

    raw = str(text or "")
    head = raw[:400]
    match = _FIRST_SENTENCE_END_RE.search(head)
    if not match:
        return raw

    first_sentence = head[: match.end()].lower()
    has_history = any(term in first_sentence for term in _CONVERSATION_META_HISTORY_TERMS)
    has_asking = any(term in first_sentence for term in _CONVERSATION_META_ASKING_TERMS)
    if not (has_history and has_asking):
        return raw
    return raw[match.end() :].lstrip()


# Anchored to the start and case-insensitive; non-greedy so a stray literal
# "</think>" inside the answer itself (a model discussing the tag) cannot
# extend the match past the first real close. `re.DOTALL` because reasoning
# is prose spanning many lines.
_THINK_BLOCK_RE = re.compile(r"^\s*<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)


def extract_reasoning_block(text: str) -> tuple[str | None, str]:
    """Split a model's VISIBLE reasoning from its answer.

    `COT_VISIBLE_REASONING_PROMPT` (app/agents/synthesizer/templates.py) asks
    for reasoning wrapped in a leading ``<think>...</think>`` block, and only
    when the caller opted in (``use_reasoning=True``). When the model
    complied, the tag is the authoritative boundary -- far more reliable than
    guessing from prose shape, which is what `strip_chain_of_thought_preamble`
    has to do for the *silent* variant of the prompt, where there is no tag to
    look for.

    Anchored to the start of the text on purpose: a ``<think>`` appearing
    mid-answer is not this system's own scaffold and is left alone as the
    model's own prose, not a leak to extract.

    Falls back to `strip_chain_of_thought_preamble`'s heuristic when no tag is
    found -- covers both the ``use_reasoning=False`` case (no tag was ever
    requested) and a ``<think>`` that never closes (truncated generation): a
    model that leaks its reasoning as prose is still caught, just with no
    ``reasoning`` text recovered, since scaffolding with no reliable closing
    marker has no safe inner boundary to extract from.
    """

    raw = str(text or "")
    match = _THINK_BLOCK_RE.match(raw)
    if not match:
        return None, strip_chain_of_thought_preamble(raw)
    reasoning = match.group(1).strip()
    remainder = raw[match.end() :].lstrip()
    return (reasoning or None), remainder


def render_reference_list(references: Sequence[EvidenceItem], language: str = "zh") -> str:
    """Render the numbered source list appended after a finished answer.

    Emitted as a markdown list because the client renders answers through
    ``react-markdown`` without ``remark-breaks``: plain newlines would collapse
    every entry onto a single line.
    """

    if not references:
        return ""
    heading = _REFERENCE_HEADINGS.get(language, _REFERENCE_HEADINGS["zh"])
    lines = [f"**{heading}**", ""]
    lines.extend(f"- [{number}] {reference_label(item, language)}" for number, item in enumerate(references, start=1))
    return "\n".join(lines)


def _reference_key(item: EvidenceItem) -> tuple[str, int | None]:
    return (item.source, item.page)


def _tidy_spacing(text: str) -> str:
    """Close the gap a removed marker leaves without disturbing line structure."""
    # Linear by construction: `_SPACE_RUN_RE` cannot fail once it has started,
    # so the scan never restarts inside a run of spaces -- the O(n^2) shape
    # python:S8786 describes (see `ingestion/processing/coreference.py`).
    tidied = _SPACE_RUN_RE.sub(_drop_space_before_punctuation, str(text or ""))
    tidied = re.sub(r"(?<!\n)[ \t]{2,}+", " ", tidied)
    return tidied.strip()


__all__ = [
    "EVIDENCE_MARKER_RE",
    "TOOL_MARKER_RE",
    "citable_tool_results",
    "citation_labels_from_contexts",
    "number_tool_markers",
    "render_tool_source_list",
    "tool_citation_labels",
    "normalize_answer_citations",
    "number_evidence_markers",
    "reference_label",
    "extract_reasoning_block",
    "render_reference_list",
    "strip_chain_of_thought_preamble",
    "strip_conversation_meta_preamble",
    "strip_model_reference_list",
]
