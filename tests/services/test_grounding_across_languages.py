"""A Chinese answer citing an English tool result is not hedged for being in another language.

Measured on the AI estimate (A4, 2026-09-28): every section of a correct answer
came back as "**基于当前可用证据，假设：**" and "基于当前可用证据，误差与局限". Two causes:

- a bold label line (`**假设：**`) merged with the line under it into one span,
  which counted as a claim and took the hedge in front of the label;
- the bullets under it cite `[T1]`, an English tool summary, and token overlap
  between a Chinese sentence and an English summary is next to nothing.

What must still hold: a number the tool did not produce is hedged, a sentence
citing nothing is judged exactly as before, and a sentence in the tool's own
language is judged by overlap as before.
"""

from __future__ import annotations

from app.services.retrieval.citation_grounding import apply_sentence_grounding, split_sentences

HEDGE = "基于当前可用证据，"

TOOL = (
    "Memory estimate for a 70B-parameter model: Inputs: params 70B, precision fp16, context 32k, batch 4. "
    "Weights = params x bytes per parameter = 70B x 2 (fp16) = 130.4 GiB. Total counted: 130.4 GiB. "
    "Not included: KV cache for 32,768 tokens: needs layers, kv_heads, head_dim, which differ by architecture "
    "and are not assumed; framework overhead and memory fragmentation."
)

ANSWER = (
    "**结论：约 130.4 GiB（仅模型权重）[T1]**\n\n"
    "**假设：**\n"
    "- 计算仅包含模型权重本身 [T1]\n"
    "- 未假设具体模型架构（如层数、注意力头数、头维度）[T1]\n\n"
    "**误差与局限：**\n"
    "未计入 KV cache、框架开销与内存碎片，实际显存需求会更高 [T1]。"
)


def _ground(answer: str, tool: str = TOOL) -> tuple[str, dict]:
    return apply_sentence_grounding(answer, [tool], tool_texts=[tool])


def test_the_measured_estimate_answer_is_not_hedged() -> None:
    grounded, report = _ground(ANSWER)

    assert HEDGE not in grounded
    assert grounded == ANSWER
    assert report["rewritten_sentences"] == 0
    assert report["tool_attributed_sentences"] >= 2


def test_a_bold_label_is_its_own_span() -> None:
    assert "**假设：**" in split_sentences("**假设：**\n- 计算仅包含模型权重本身 [T1]")


def test_a_list_introduction_is_its_own_span() -> None:
    """Measured in the fourth A4 run: `此估算**未计入** [T1]：` took the hedge."""

    text = "此估算**未计入** [T1]：\n1. KV cache 的显存占用\n2. 框架开销与内存碎片"
    grounded, _ = _ground(text)

    assert "此估算**未计入** [T1]：" in split_sentences(text)
    assert not grounded.startswith(HEDGE)


def test_list_numbering_is_not_a_figure() -> None:
    grounded, _ = _ground(
        "未计入以下几项，实际显存需求会更高 [T1]：\n1. 激活值\n2. 框架开销与内存碎片带来的额外占用 [T1]。"
    )

    assert HEDGE not in grounded


def test_a_number_the_tool_did_not_produce_is_still_hedged() -> None:
    grounded, _ = _ground("需要 8 张 80GB 显卡，总价约 200 万元 [T1]。")

    assert HEDGE in grounded


def test_every_number_must_be_the_tools() -> None:
    """160 is not the tool's, so the sentence is not borne out."""

    grounded, _ = _ground("权重之外还要再加 160 GiB 给缓存 [T1]。")

    assert HEDGE in grounded


def test_numbers_that_are_the_tools_carry_the_sentence() -> None:
    grounded, _ = _ground("按 32k 上下文、batch 4 计算，权重约 130.4 GiB [T1]。")

    assert HEDGE not in grounded


def test_a_sentence_citing_nothing_is_judged_as_before() -> None:
    grounded, _ = _ground("实际部署时通常还需要预留大量余量用于峰值流量和意外情况。")

    assert HEDGE in grounded


def test_a_marker_with_no_tool_behind_it_attributes_nothing() -> None:
    grounded, _ = _ground("实际部署时通常还需要预留大量余量用于峰值流量和意外情况 [T3]。")

    assert HEDGE in grounded


def test_a_sentence_in_the_tools_own_language_is_judged_by_overlap() -> None:
    """No script gap, so no pass: overlap measures it, and this one shares nothing."""

    grounded, _ = apply_sentence_grounding(
        "Deployment usually wants generous headroom during traffic spikes [T1].",
        [TOOL],
        language="en",
        tool_texts=[TOOL],
    )

    assert grounded.startswith("Based on the available evidence")


def test_without_tool_texts_nothing_changes() -> None:
    """A caller that passes no tools gets the previous behaviour exactly."""

    grounded, report = apply_sentence_grounding(
        "- 未计入 KV cache、框架开销与内存碎片，实际显存需求会更高 [T1]。", [TOOL]
    )

    assert HEDGE in grounded
    assert report["tool_attributed_sentences"] == 0
