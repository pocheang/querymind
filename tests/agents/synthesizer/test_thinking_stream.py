"""ReasoningStreamSplitter: the real-time half of the visible-reasoning
feature. `extract_reasoning_block` (test_reasoning_extraction.py) does the
same split after the fact, on the complete text; this one has to do it live,
one arbitrarily-sized chunk at a time, without ever emitting a partial
`<think>`/`</think>` tag as plain text on either channel.
"""

from __future__ import annotations

from app.agents.synthesizer.thinking_stream import ReasoningStreamSplitter


def _feed_all(splitter: ReasoningStreamSplitter, chunks: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for chunk in chunks:
        out.extend(splitter.feed(chunk))
    out.extend(splitter.finish())
    return out


def _by_channel(pairs: list[tuple[str, str]], channel: str) -> str:
    return "".join(text for ch, text in pairs if ch == channel)


def test_a_single_chunk_with_both_tags_splits_cleanly():
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, ["<think>reasoning here</think>the answer"])

    assert _by_channel(pairs, "thought") == "reasoning here"
    assert _by_channel(pairs, "answer") == "the answer"


def test_tags_split_across_many_small_chunks():
    """The exact shape a real token stream produces: neither tag arrives whole."""
    full = "<think>\nStep 1: analyze\nStep 2: assess\n</think>\nBM25 is a ranking function [E1]."
    chunks = [full[i : i + 3] for i in range(0, len(full), 3)]

    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, chunks)

    assert "<think>" not in _by_channel(pairs, "thought")
    assert "</think>" not in _by_channel(pairs, "thought")
    assert "<think>" not in _by_channel(pairs, "answer")
    assert "</think>" not in _by_channel(pairs, "answer")
    assert _by_channel(pairs, "thought") == "\nStep 1: analyze\nStep 2: assess\n"
    assert _by_channel(pairs, "answer") == "\nBM25 is a ranking function [E1]."


def test_the_open_tag_split_one_character_at_a_time():
    """The narrowest possible chunking: still must not leak a partial tag."""
    full = "<think>x</think>y"
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, list(full))

    assert _by_channel(pairs, "thought") == "x"
    assert _by_channel(pairs, "answer") == "y"


def test_a_model_that_never_opens_the_tag_reads_entirely_as_answer():
    """No `<think>` at all -- a model that ignored the instruction, or was
    never asked (use_reasoning=False upstream never selects the visible
    prompt, but the splitter itself does not know that; it must degrade
    safely regardless of why the tag is absent)."""
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, ["This is a perfectly ordinary answer with no reasoning block at all."])

    assert _by_channel(pairs, "thought") == ""
    assert _by_channel(pairs, "answer") == "This is a perfectly ordinary answer with no reasoning block at all."


def test_a_short_answer_under_the_sniff_limit_is_not_held_back_forever():
    """`finish()` must still flush a short answer that never crossed the
    sniff threshold mid-stream -- the case that would be missed by a
    splitter that only resolves state inside `feed()`."""
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, ["No."])

    assert pairs == [("answer", "No.")]


def test_an_opened_block_that_never_closes_flushes_as_thought_on_finish():
    """Truncated generation: `<think>` opened, the stream ends before
    `</think>`. `extract_reasoning_block` makes the same call independently
    on the complete text; this is the live-streaming side of that same
    malformed case."""
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, ["<think>a partial thought that never closes"])

    assert _by_channel(pairs, "answer") == ""
    assert "a partial thought that never closes" in _by_channel(pairs, "thought")


def test_text_before_the_opening_tag_is_reported_as_answer():
    """The prompt asks for <think> to be the very first thing written; a
    model that adds a stray character or two ahead of it should not have
    that leading text silently dropped."""
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, ["Sure, <think>reasoning</think>answer"])

    assert _by_channel(pairs, "answer") == "Sure, answer"
    assert _by_channel(pairs, "thought") == "reasoning"


def test_a_stray_closing_tag_inside_the_answer_does_not_reopen_thinking():
    """Once past `</think>`, the splitter is in its fast path and stops
    looking for tags at all -- a model discussing the tag itself in its
    answer must not be misread as a second reasoning block."""
    splitter = ReasoningStreamSplitter()
    pairs = _feed_all(splitter, ["<think>t</think>The tag is written as </think> in the docs."])

    assert _by_channel(pairs, "thought") == "t"
    assert _by_channel(pairs, "answer") == "The tag is written as </think> in the docs."
