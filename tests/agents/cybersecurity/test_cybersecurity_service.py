"""What the cybersecurity specialist contributes, and what it delegates.

These tests were rewritten. Their previous form asserted the hardcoded fallback
template -- `"安全工具与漏洞研判发现" in candidate.text`, and for an empty corpus
`"本地知识库未检索到直接匹配的安全策略"` -- which was the ONLY path production
ever took, because the single construction site supplied no `model_invoker`. A
test that pins a template nobody chose makes the accident look like a decision.

What the agent is now: a skill choice, an indicator extraction, and a
delegation to `SynthesizerAgentService`. So that is what is asserted -- the
generation itself is that service's to test, and it already is.
"""

import pytest

from app.agents.cybersecurity.service import (
    INDICATORS_TOOL_ID,
    PIPELINE_SKILLS,
    CybersecurityAgentService,
    extract_security_indicators,
    indicator_tool_result,
)
from app.agents.shared.config import VALID_SKILLS
from app.domain.contracts import EvidenceItem
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest, RequestActor


def test_extract_security_indicators() -> None:
    text = (
        "Server 10.0.0.1 and 192.168.1.100 were compromised by CVE-2021-44228. "
        "MD5 hash 5d41402abc4b2a76b9719d911017c592 was observed. 127.0.0.1 is loopback."
    )
    indicators = extract_security_indicators(text)
    assert "CVE-2021-44228" in indicators["cves"]
    assert "10.0.0.1" in indicators["ips"]
    assert "192.168.1.100" in indicators["ips"]
    assert "127.0.0.1" not in indicators["ips"]
    assert "5d41402abc4b2a76b9719d911017c592" in indicators["hashes"]


@pytest.mark.asyncio
async def test_it_delegates_generation_rather_than_writing_the_answer_itself() -> None:
    """The whole change, as one assertion.

    Delegation is what buys the real chat model, `asyncio.to_thread`, streaming
    into `AnswerStreamStore`, `[E{k}]` allow-listing and the documented
    no-evidence answer. A specialist that generated its own text would have to
    reimplement all five, and the version that did reimplemented none of them.
    """

    seen: dict[str, object] = {}

    class _Recording:
        async def synthesize_candidate(self, request, context, tool_results, skill):  # noqa: ANN001
            seen.update(request=request, context=context, tool_results=tool_results, skill=skill)
            return CandidateAnswer(text="generated [E1]")

    agent = CybersecurityAgentService(synthesizer=_Recording())
    req = OrchestrationRequest(
        question="What is the mitigation for CVE-2021-44228 Log4Shell?",
        actor=RequestActor(user_id="analyst", tenant_id="t1", role="admin"),
    )
    context = ContextBundle(
        evidence=(
            EvidenceItem(
                item_id="ev_cyber_1",
                document_id="doc_advisory",
                source="cve_bulletin.pdf",
                content="Log4Shell JNDI vulnerability allows RCE. Patch to 2.17.1 immediately.",
            ),
        )
    )

    candidate = await agent.synthesize_candidate(req, context, (), "cyber_attack_analysis")

    assert candidate.text == "generated [E1]"
    assert seen["request"] is req
    assert seen["context"] is context


@pytest.mark.parametrize(("domain_skill", "pipeline_skill"), sorted(PIPELINE_SKILLS.items()))
def test_every_domain_skill_maps_onto_a_skill_the_pipeline_knows(domain_skill: str, pipeline_skill: str) -> None:
    """A mapping to a name `skills.py` does not know silently degrades to
    keyword inference, which is the behaviour the specialist exists to replace.
    Parametrized so a failure names the skill."""

    assert pipeline_skill in VALID_SKILLS


@pytest.mark.asyncio
async def test_an_unknown_skill_still_reaches_a_domain_shape() -> None:
    """A skill nobody mapped must not fall through to the general template --
    this is a security specialist, and the fallback is a security shape."""

    seen: dict[str, object] = {}

    class _Recording:
        async def synthesize_candidate(self, request, context, tool_results, skill):  # noqa: ANN001
            seen["skill"] = skill
            return CandidateAnswer(text="x")

    agent = CybersecurityAgentService(synthesizer=_Recording())
    req = OrchestrationRequest(question="q", actor=RequestActor(user_id="u", tenant_id="t", role="user"))
    await agent.synthesize_candidate(req, ContextBundle(evidence=()), (), "skill_nobody_declared")

    assert seen["skill"] == "cyber_attack_analysis"
    assert seen["skill"] in VALID_SKILLS


@pytest.mark.asyncio
async def test_extracted_indicators_arrive_as_a_tool_finding_not_as_evidence() -> None:
    """Indicators are derived by regex from material the model can already read.

    Presented as evidence they would invite a citation pointing at a derivation
    rather than at a source, which is the citation-first rule read backwards. A
    tool observation is what they are, and `_render_tool_results` already labels
    them as such.
    """

    seen: dict[str, object] = {}

    class _Recording:
        async def synthesize_candidate(self, request, context, tool_results, skill):  # noqa: ANN001
            seen["tool_results"] = tool_results
            seen["context"] = context
            return CandidateAnswer(text="x")

    agent = CybersecurityAgentService(synthesizer=_Recording())
    req = OrchestrationRequest(
        question="10.0.0.1 上出现了 CVE-2021-44228 的利用迹象",
        actor=RequestActor(user_id="u", tenant_id="t", role="user"),
    )
    context = ContextBundle(evidence=())

    await agent.synthesize_candidate(req, context, ())

    results = seen["tool_results"]
    assert any(r.tool_id == INDICATORS_TOOL_ID for r in results)
    summary = next(r.summary for r in results if r.tool_id == INDICATORS_TOOL_ID)
    assert "CVE-2021-44228" in summary and "10.0.0.1" in summary
    # The context handed on is unchanged: nothing was injected into the evidence.
    assert seen["context"] is context


def test_no_indicator_result_is_produced_when_there_are_no_indicators() -> None:
    """The direction that keeps the test above meaningful: it must not pass
    because a tool result is appended unconditionally."""

    assert indicator_tool_result({"cves": [], "ips": [], "hashes": []}) == ()
