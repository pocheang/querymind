"""The answer a reader sees must not contain the machinery that produced it.

Found by reading one on screen. A single question came back as:

    基于当前可用证据，基于当前本地检索结果，我对"What is reciprocal rank fusion?基于当前
    可用证据，"的回答如下： 1.基于当前可用证据， [1] document=https://<PATH_1>
    source=https://<PATH_2> layer=web; retriever=web Reciprocal Rank Fusion ...
    2.基于当前可用证据，无 答案模板指导（Skill: answer_with_citations）： Answer
    template for concept explanation: ... Citation rules: - EVERY factual claim
    MUST have an evidence-marker citation ...

Four separate defects, in two files:

`LocalEvidenceChatModel` (app/services/models/runtime.py)
  1. narrated itself ("我对…的回答如下") and closed with a paragraph about
     configuring Ollama;
  2. echoed `ContextBuilder`'s addressing header (`[E1] document=…; layer=…;
     retriever=…`), which is metadata, not prose;
  3. `_extract_section` terminated only on labels ending in `上下文:`, so the last
     section ran to the end of the prompt and swallowed the answer template --
     the model's own instructions came back as part of the answer.

`apply_sentence_grounding` (app/services/retrieval/citation_grounding.py)
  4. treated a bare citation marker as a sentence, scored it unsupported, and
     prefixed it -- hedging the attribution rather than the claim.
"""

from __future__ import annotations

import re

import pytest

from app.services.models.runtime import LocalEvidenceChatModel
from app.services.retrieval.citation_grounding import apply_sentence_grounding

PROMPT = """[Language: en]
技能: answer_with_citations

用户问题:
What is reciprocal rank fusion?

记忆上下文:
无

向量检索上下文:
无

图谱上下文:
无

联网补充上下文:
[E1] document=https://example.org/rrf; source=https://example.org/rrf; layer=web; retriever=web
Reciprocal Rank Fusion merges rankings mathematically. It gives credit to items ranked high in several lists.

答案模板指导（Skill: answer_with_citations）：
Answer template for concept explanation:
1. Core definition with citation [E1]
Citation rules:
- EVERY factual claim MUST have an evidence-marker citation, e.g. [E1]
"""


@pytest.fixture
def answer() -> str:
    return LocalEvidenceChatModel().invoke([("human", PROMPT)]).content


class TestTheOfflineAnswerIsAnAnswer:
    def test_the_prompt_does_not_come_back_in_it(self, answer: str) -> None:
        """The defect that made the answer unreadable: the template section was
        parsed as part of the last evidence block."""
        assert "答案模板指导" not in answer
        assert "Answer template" not in answer
        assert "EVERY factual claim MUST" not in answer

    def test_the_addressing_header_is_not_prose(self, answer: str) -> None:
        for fragment in ("document=", "source=", "layer=web", "retriever="):
            assert fragment not in answer

    def test_it_does_not_narrate_itself(self, answer: str) -> None:
        """A note about which backend ran belongs in the trace, not in every
        answer the reader has to read past."""
        assert "回答如下" not in answer
        assert "Ollama" not in answer
        assert "离线后端" not in answer

    def test_the_placeholder_for_an_empty_section_is_not_content(self, answer: str) -> None:
        assert not answer.lstrip().startswith("无")

    def test_it_carries_the_marker_of_what_it_quoted(self, answer: str) -> None:
        """Without a marker there is nothing for `output_filter` to renumber, so
        the reference list it appends points at citations the text never made."""
        assert "[E1]" in answer

    def test_it_says_something(self, answer: str) -> None:
        assert "Reciprocal Rank Fusion" in answer

    def test_no_evidence_is_reported_as_no_evidence(self) -> None:
        empty = PROMPT.replace(
            "[E1] document=https://example.org/rrf; source=https://example.org/rrf; layer=web; retriever=web\n"
            "Reciprocal Rank Fusion merges rankings mathematically. "
            "It gives credit to items ranked high in several lists.",
            "无",
        )
        text = LocalEvidenceChatModel().invoke([("human", empty)]).content

        assert "[E" not in text
        assert "检索" in text


class TestGroundingLeavesStructureAlone:
    EVIDENCE = ["Reciprocal Rank Fusion merges rankings mathematically."]

    def test_a_bare_citation_marker_is_not_hedged(self) -> None:
        """`基于当前可用证据，[E1]` reads as doubt about the citation itself."""
        text = "Reciprocal Rank Fusion merges rankings mathematically.\n\n[E1]"
        grounded, _ = apply_sentence_grounding(text, self.EVIDENCE)

        assert grounded == text

    def test_a_url_is_not_split_through_the_middle(self) -> None:
        """The dot in a hostname is not a full stop, and hedging what followed it
        spliced the prefix into the link: `https://x.基于当前可用证据，example/a`."""
        text = "See https://arxiv.org/abs/2505.08728 for the assessment framework. [E1]"
        grounded, _ = apply_sentence_grounding(text, self.EVIDENCE)

        assert "https://arxiv.org/abs/2505.08728" in grounded

    def test_a_heading_is_not_hedged(self) -> None:
        text = "Merges rankings mathematically. [E1]\n\n**参考来源**\n\n- [1] https://example.org/rrf"
        grounded, _ = apply_sentence_grounding(text, self.EVIDENCE)

        assert "**参考来源**" in grounded
        assert "- [1] https://example.org/rrf" in grounded

    def test_untouched_text_keeps_its_whitespace(self) -> None:
        """Rejoining the pieces with one separator reflowed paragraph breaks and
        list indentation into a single space."""
        text = "Merges rankings mathematically. [E1]\n\n- and gives credit to top-ranked items. [E1]"
        grounded, _ = apply_sentence_grounding(text, self.EVIDENCE)

        assert "\n\n- " in grounded

    def test_the_hedge_goes_before_the_claim_not_the_bullet(self) -> None:
        text = "- entirely unrelated assertion about Argentine monetary policy."
        grounded, _ = apply_sentence_grounding(text, self.EVIDENCE)

        assert grounded.startswith("- Based on the available evidence, ")

    def test_a_genuinely_unsupported_claim_is_still_hedged(self) -> None:
        """The fixes must not turn the check off -- that would trade a cosmetic
        bug for a truthfulness one."""
        text = "Quantum tunnelling drives inflation in Argentina."
        grounded, report = apply_sentence_grounding(text, self.EVIDENCE)

        assert grounded.startswith("Based on the available evidence, ")
        assert report["rewritten_sentences"] == 1

    def test_the_hedge_matches_the_answers_own_language_not_the_evidences(self) -> None:
        """Observed live on a follow-up question (2026-09-15): an English answer
        came back as "基于当前可用证据，The provided evidence does not contain
        information about BM25's limitations." -- the hedge is spliced in after
        generation, so it has to match what the model actually wrote, in either
        direction, regardless of what language the evidence happens to be in."""
        chinese_evidence = ["互惠排名融合是一种数学上合并排名的方法。"]

        english_answer = "Quantum tunnelling drives inflation in Argentina."
        grounded_en, _ = apply_sentence_grounding(english_answer, chinese_evidence)
        assert grounded_en.startswith("Based on the available evidence, ")

        chinese_answer = "量子隧穿效应导致了阿根廷的通货膨胀。"
        grounded_zh, _ = apply_sentence_grounding(chinese_answer, self.EVIDENCE)
        assert grounded_zh.startswith("基于当前可用证据，")

    def test_a_supported_claim_is_left_alone(self) -> None:
        text = "Reciprocal Rank Fusion merges rankings mathematically. [E1]"
        grounded, report = apply_sentence_grounding(text, self.EVIDENCE)

        assert grounded == text
        assert report["rewritten_sentences"] == 0

    def test_a_sentence_that_already_declines_to_answer_is_not_hedged_twice(self) -> None:
        """Observed live (2026-09-15): asked for facts the evidence did not
        cover, the model wrote "Based on the provided information, I cannot
        supply three unrelated random facts about deep sea creatures." --
        already a refusal -- and it came back as "Based on the available
        evidence, Based on the provided information, I cannot supply...".
        None of the five original `_HEDGE_MARKERS` match ordinary English
        "I cannot" / "unable to" / "does not contain" phrasing, so the
        sentence scored as an unhedged claim and got a second, redundant
        qualifier stacked in front of its own."""
        text = (
            "Based on the provided information, I cannot supply three unrelated random facts about deep sea creatures."
        )
        grounded, report = apply_sentence_grounding(text, self.EVIDENCE)

        assert grounded == text
        assert report["rewritten_sentences"] == 0

    def test_other_common_self_disclaimer_shapes_are_recognised_too(self) -> None:
        for text in (
            "I could not find any evidence covering that topic.",
            "The model was unable to determine an answer from the provided context.",
            "The retrieved context does not contain information about BM25's limitations.",
        ):
            grounded, report = apply_sentence_grounding(text, self.EVIDENCE)
            assert grounded == text, text
            assert report["rewritten_sentences"] == 0, text

    def test_a_chinese_sentence_that_declines_to_answer_is_not_hedged_twice(self) -> None:
        """The same defect as the English case above, in the language this
        application is mostly used in -- and it survived that fix because only
        the English phrasings were added to `_HEDGE_MARKERS`.

        Observed live (2026-09-16) on a web-search question the retrieval
        stage could not answer. The model wrote a plain disclaimer and the
        reader saw it hedged into self-contradiction:

            基于当前可用证据，但需要说明的是，本轮回答基于上一轮查询的记忆
            信息，当前未获取到新的联网数据。

        "当前未获取到新的联网数据" is the sentence saying it HAS no evidence,
        so prefixing it with "based on the available evidence" asserts the
        opposite of what follows it.
        """
        text = "但需要说明的是，本轮回答基于上一轮查询的记忆信息，当前未获取到新的联网数据。"
        grounded, report = apply_sentence_grounding(text, self.EVIDENCE)

        assert grounded == text
        assert report["rewritten_sentences"] == 0

    def test_other_chinese_self_disclaimer_shapes_are_recognised_too(self) -> None:
        for text in (
            "当前检索结果中未包含该主题的相关内容。",
            "现有证据无法支撑这一结论。",
            "检索未能获取到与该问题相关的资料。",
            "所提供的上下文没有提到该指标的具体数值。",
        ):
            grounded, report = apply_sentence_grounding(text, self.EVIDENCE)
            assert grounded == text, text
            assert report["rewritten_sentences"] == 0, text

    def test_a_chinese_claim_that_merely_mentions_evidence_is_still_hedged(self) -> None:
        """The guard above must key on the sentence disclaiming its own
        support, not on it containing any of those characters. A sentence that
        makes an unsupported assertion while happening to use the word 获取 or
        包含 is still an unsupported assertion."""
        for text in (
            "该系统每秒可获取十万条阿根廷通胀数据。",
            "这份文档包含了量子隧穿效应的完整推导。",
        ):
            grounded, report = apply_sentence_grounding(text, self.EVIDENCE)
            assert grounded.startswith("基于当前可用证据，"), text
            assert report["rewritten_sentences"] == 1, text


class TestEveryRetrievedSourceIsUsed:
    """One paragraph and one reference for a four-source answer.

    `_extract_section` has now been wrong in both directions. Terminating only
    on labels ending in `上下文:` let the last section run to the end of the
    prompt and swallow the answer template. Replacing that with "a short line
    ending in a colon" cut the section at *every piece of evidence*, because
    `[E2] document=https:` reaches a colon within a few characters -- so all but
    the first excerpt was silently discarded, and the reader saw a single
    citation for a search that had returned four.

    The terminator is now the set of labels `_build_prompt_with_language`
    actually writes.
    """

    @staticmethod
    def _rendered(count: int) -> str:
        return "\n\n".join(
            f"[E{i}] document=https://example.org/{i}, version=1; "
            f"source=https://example.org/{i}; layer=web; retriever=web\n"
            f"Fact number {i} about reciprocal rank fusion, stated plainly."
            for i in range(1, count + 1)
        )

    def _answer_for(self, count: int) -> str:
        import app.agents.synthesizer.generation as generation

        prompt = generation._build_prompt_with_language(
            "What is reciprocal rank fusion?",
            "en",
            "answer_with_citations",
            vector_context=self._rendered(count),
        )
        return LocalEvidenceChatModel().invoke([("human", prompt)]).content

    def test_four_sources_produce_four_citations(self) -> None:
        answer = self._answer_for(4)

        assert sorted(set(re.findall(r"\[E\d+\]", answer))) == ["[E1]", "[E2]", "[E3]", "[E4]"]

    def test_a_url_in_the_evidence_does_not_end_the_section(self) -> None:
        """The exact character that broke it: the colon in `https:`."""
        assert "[E2]" in self._answer_for(2)

    def test_each_marker_keeps_its_own_excerpt(self) -> None:
        """Misattribution would be worse than truncation: it credits a claim to a
        source that does not support it."""
        answer = self._answer_for(4)
        pairs = re.findall(r"Fact number (\d+)[^\n]*\[E(\d+)\]", answer)

        assert pairs, "no cited excerpts in the answer"
        for fact, marker in pairs:
            assert fact == marker, f"[E{marker}] carries fact {fact}"


# --- the sandbox wrapper and the tool block, fixed 2026-09-21 ---------------
#
# The same failure this file opens with, in the shape it takes once a query uses
# a tool. `SynthesizerAgentService` concatenated the governed tool block onto
# `vector_context`, so the prompt builder wrapped BOTH in
# `<retrieved_evidence_sandbox nonce="...">`, and `_cited_excerpts` let the last
# excerpt's body run to the end of the section. Measured on the shipped code:
#
#   年假每年 10 天。 Governed tool results (report these to the user; an
#   `approval_required` action has NOT been performed yet): Tool 1
#   (querymind_cyber_cve_lookup) -> succeeded: CVE-2021-44228 CVSS 10.0
#   </retrieved_evidence_sandbox> [E1]
#
# Two layers were wrong, and both are fixed rather than one papering over the
# other: tool results now get their own prompt section OUTSIDE the untrusted
# evidence sandbox, and the stand-in strips sandbox delimiters before reading an
# excerpt.

SANDBOXED_PROMPT = """[Language: zh]
技能: answer_with_citations

用户问题:
<untrusted_user_input nonce="abc123">
年假多少天
</untrusted_user_input>

记忆上下文:
无

向量检索上下文:
<retrieved_evidence_sandbox nonce="abc123">
[E1] document=d1; source=a.md; layer=evidence; retriever=bm25
年假每年 10 天，满 10 年为 15 天。
</retrieved_evidence_sandbox>

图谱上下文:
无

联网补充上下文:
无

工具执行结果:
Governed tool results (report these to the user; an `approval_required` action has NOT been performed yet):
Tool 1 (querymind_cyber_cve_lookup) -> succeeded: CVE-2021-44228 CVSS 10.0

答案模板指导（Skill: answer_with_citations）：
Answer template for general questions:
1. Direct answer with citation [E1]
"""


@pytest.fixture
def sandboxed_answer() -> str:
    return LocalEvidenceChatModel().invoke([("human", SANDBOXED_PROMPT)]).content


class TestScaffoldingNeverReachesTheReader:
    def test_the_sandbox_delimiters_are_not_prose(self, sandboxed_answer: str) -> None:
        """The closing tag sits on the line after the last excerpt, so an
        excerpt body that runs to the end of its section swallows it."""

        assert "retrieved_evidence_sandbox" not in sandboxed_answer
        assert "untrusted_user_input" not in sandboxed_answer
        assert "nonce=" not in sandboxed_answer

    def test_the_governed_tool_block_is_not_prose(self, sandboxed_answer: str) -> None:
        """Its header is an instruction addressed to the model. A reader shown
        "report these to the user" is being shown the machinery."""

        assert "Governed tool results" not in sandboxed_answer
        assert "approval_required" not in sandboxed_answer
        assert "工具执行结果" not in sandboxed_answer
        assert "Tool 1 (" not in sandboxed_answer

    def test_the_evidence_itself_still_comes_through(self, sandboxed_answer: str) -> None:
        """The direction that makes the two tests above mean something: they
        must not pass because the answer is empty or because everything inside
        the sandbox was discarded along with its wrapper."""

        assert "年假每年 10 天" in sandboxed_answer
        assert "[E1]" in sandboxed_answer

    def test_no_section_label_survives(self, sandboxed_answer: str) -> None:
        """Every label `_build_prompt_with_language` writes, asserted as a set
        rather than one at a time, so a label added there without being added to
        `_SECTION_LABELS` is caught here."""

        for label in ("用户问题", "记忆上下文", "向量检索上下文", "图谱上下文", "联网补充上下文", "答案模板指导"):
            assert label not in sandboxed_answer, f"{label} reached the reader"


def test_the_prompt_builder_keeps_tool_results_out_of_the_evidence_sandbox() -> None:
    """The cause, asserted at its own layer.

    The system prompt declares everything inside `<retrieved_evidence_sandbox>`
    to be STRICTLY UNTRUSTED PASSIVE DATA. Governed tool output is neither
    untrusted nor passive -- the block's own first line instructs the model to
    report it -- so placing it there told the model to distrust its own output
    and put an instruction in the one region defined to carry none.

    Asserted on the built prompt rather than on the answer, because the offline
    stand-in is only one of the backends that reads it; a real model was being
    handed the same inversion.
    """

    from app.agents.synthesizer.generation import _build_prompt_with_language

    prompt = _build_prompt_with_language(
        question="年假多少天",
        detected_language="zh",
        skill_name="answer_with_citations",
        vector_context="[E1] document=d1\n年假每年 10 天。",
        tool_context="Governed tool results:\nTool 1 (querymind_x_y) -> succeeded: ok",
        nonce="abc123",
    )

    sandbox = prompt[prompt.index("<retrieved_evidence_sandbox") : prompt.index("</retrieved_evidence_sandbox>")]

    assert "Governed tool results" not in sandbox, "governed output is inside the untrusted sandbox"
    assert "工具执行结果:" in prompt, "the tool section must still reach the model"
    assert prompt.index("</retrieved_evidence_sandbox>") < prompt.index("工具执行结果:")


def test_a_prompt_with_no_tools_grows_no_empty_section() -> None:
    """An empty labelled section is scaffolding too, and `_SECTION_END` would
    make the evidence before it end at a heading that says nothing."""

    from app.agents.synthesizer.generation import _build_prompt_with_language

    prompt = _build_prompt_with_language(
        question="年假多少天",
        detected_language="zh",
        skill_name="answer_with_citations",
        vector_context="[E1] document=d1\n年假每年 10 天。",
        nonce="abc123",
    )

    assert "工具执行结果" not in prompt


WEB_EVIDENCE_THEN_TOOLS_PROMPT = """[Language: zh]
技能: answer_with_citations

用户问题:
年假多少天

记忆上下文:
无

向量检索上下文:
无

图谱上下文:
无

联网补充上下文:
<retrieved_evidence_sandbox nonce="abc123">
[E1] document=https://example.org/leave; source=https://example.org/leave; layer=web; retriever=web
年假每年 10 天，满 10 年为 15 天。
</retrieved_evidence_sandbox>

工具执行结果:
Governed tool results (report these to the user; an `approval_required` action has NOT been performed yet):
Tool 1 (querymind_cyber_cve_lookup) -> succeeded: CVE-2021-44228 CVSS 10.0

答案模板指导（Skill: answer_with_citations）：
Answer template for general questions:
1. Direct answer with citation [E1]
"""


def test_the_tool_section_ends_the_evidence_section_before_it() -> None:
    """The case `工具执行结果` has to be in `_SECTION_LABELS` for, and the one
    the tests above did not reach.

    In those, the tool section follows `联网补充上下文: 无`, so there is no
    excerpt in front of it and removing the label from `_SECTION_LABELS`
    reddened NOTHING -- a mutation finding a gap in the tests rather than a bug
    in the code, for the fourth time in this review.

    Here the last evidence lives in the web section, so the tool block is the
    very next thing after an excerpt: without the label, that excerpt's body
    runs straight into it, which is the original defect with one section's
    difference.
    """

    answer = LocalEvidenceChatModel().invoke([("human", WEB_EVIDENCE_THEN_TOOLS_PROMPT)]).content

    assert "年假每年 10 天" in answer, "the excerpt itself must survive"
    assert "Governed tool results" not in answer
    assert "Tool 1 (" not in answer
    assert "CVE-2021-44228" not in answer, "a tool finding is not part of the web excerpt"


def test_the_sandbox_pattern_has_no_competing_quantifiers() -> None:
    """The stripper runs over a prompt that carries the user's question.

    Its first form was `(?:\\s+[^>]*)?` -- `\\s+` and `[^>]*` competing for the
    same whitespace run, the adjacent-quantifier shape this repository records
    under `S8786`. CodeQL caught it on the pull request that introduced it
    ("Polynomial regular expression used on uncontrolled data"), naming
    `'<untrusted_user_input' + many tabs` as the input. Measured, it was
    quadratic: 18.6ms at n=2000 against 1180.7ms at n=16000; the replacement is
    0.006ms and 0.028ms.

    **The first version of this test could not fail**, and that is worth more
    than the fix. It asserted that `match` is None at offsets inside the tab run
    and that `sub` terminates -- but a tab is not `<`, so the old pattern is
    rejected in one step at those offsets too, and `sub` terminates either way,
    just slowly. Restoring the quadratic form left all 31 assertions green (0.83s
    -> 2.80s). The only thing that differed was the clock, and a clock is what
    this repository says not to assert on in CI.

    So the property is asserted where it actually lives: on the compiled
    object's own source, that no two quantifiers able to match the same
    whitespace sit next to each other. Structural rather than behavioural
    because the defect is structural -- and read off `pattern.pattern`, the
    shipped object, never a copy written into the test.
    """

    import re as _re

    from app.services.models.runtime import _SANDBOX_DELIMITER_RE as pattern

    source = pattern.pattern

    # `\s+` or `\s*` immediately followed by a class that also accepts
    # whitespace is the shape that backtracks. Exactly the old form.
    assert _re.search(r"\\s[+*]\s*\[\^", source) is None, (
        f"two quantifiers compete for the same whitespace run: {source!r}"
    )

    # And the behaviour that shape existed to provide is still there.
    assert pattern.sub("", '<retrieved_evidence_sandbox nonce="abc">x</retrieved_evidence_sandbox>') == "x"
    assert pattern.sub("", "<untrusted_user_input\tnonce='1'>y") == "y"
    # The tag-name boundary a bare `[^>]*` would lose.
    assert pattern.sub("", "<retrieved_evidence_sandboxfoo>x") == "<retrieved_evidence_sandboxfoo>x"


def test_the_sandbox_pattern_strips_what_the_builder_emits() -> None:
    """Pinned against the real producer, not against a copy of the old regex.

    The stripper and `SandboxedPromptBuilder` are two halves of one convention:
    the builder writes the wrapper, this reads it back off. A test that compared
    the new pattern with a transcription of the old one would keep passing on
    the day the builder's format changes and the stripper silently stops
    matching -- which is the failure this repository records for the dead-class
    audit and the sensitive-content gate alike.

    So the wrapper is generated here, by the code that generates it in
    production, and the assertion is that stripping it leaves exactly the body.
    """

    from app.services.models.runtime import _SANDBOX_DELIMITER_RE as pattern
    from app.services.security.injection_defense import SandboxedPromptBuilder

    nonce = SandboxedPromptBuilder.generate_nonce()
    body = "年假每年 10 天，满 10 年为 15 天。"

    for wrapped in (
        SandboxedPromptBuilder.sandbox_evidence_context(body, nonce),
        SandboxedPromptBuilder.sandbox_user_query(body, nonce),
    ):
        assert nonce in wrapped, "the fixture must actually carry a nonce"
        stripped = pattern.sub("", wrapped).strip()
        assert stripped == body, f"{wrapped!r} -> {stripped!r}"
        assert nonce not in stripped


def test_the_sandbox_pattern_is_bounded_everywhere() -> None:
    """Finite by construction rather than by measurement.

    CodeQL named two inputs against earlier forms of this pattern. The second
    was measured LINEAR (0.85ms over 176KB, doubling with the input), so the
    alert over-approximated -- but an over-approximation still leaves the check
    red, and arguing with a scanner is not a fix. Every repetition here is
    bounded, so there is nothing left to over-approximate.

    **The first version of this assertion missed half of what it claimed.** It
    looked for `\\s+` and `\\s*` by name, so opening `[ \\t\\r\\n]{0,4}` back up to
    `[ \\t\\r\\n]*` -- the same unbounded run written as a character class --
    reddened nothing. The property is "no unbounded repetition", not "no
    unbounded `\\s`", so that is what it says now: character classes are removed
    first, then no `*` or `+` may remain anywhere.
    """

    import re as _re

    from app.services.models.runtime import _SANDBOX_DELIMITER_RE as pattern

    source = pattern.pattern
    # Remove character-class bodies, where `*` and `+` would be literals rather
    # than quantifiers, so what is left is only the quantifier positions.
    outside_classes = _re.sub(r"\[(?:\\.|[^\]\\])*\]", "CLASS", source)

    for greedy in ("*", "+"):
        assert greedy not in outside_classes, (
            f"unbounded repetition {greedy!r} in {source!r}; every run here must be bounded"
        )
    # And no `{m,}` with an open upper bound.
    for low, high in _re.findall(r"\{(\d*),(\d*)\}", source):
        assert high, f"open-ended repetition {{{low},}} in {source!r}"
