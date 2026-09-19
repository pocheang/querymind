"""Unit tests for CybersecurityAgentService."""

import pytest

from app.agents.cybersecurity.service import (
    CYBERSECURITY_SYSTEM_PROMPT,
    CybersecurityAgentService,
    extract_security_indicators,
)
from app.domain.contracts import EvidenceItem, ToolResult
from app.domain.workflow import ContextBundle
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
async def test_cybersecurity_agent_deterministic_synthesis() -> None:
    agent = CybersecurityAgentService()
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
    tool_results = (
        ToolResult(
            tool_id="querymind_cyber_cve_lookup",
            status="succeeded",
            summary="CVE-2021-44228 Log4Shell (CVSS 10.0): Upgrade Log4j to >= 2.17.1.",
        ),
    )

    candidate = await agent.synthesize_candidate(
        request=req,
        context=context,
        tool_results=tool_results,
        skill="cyber_attack_analysis",
    )

    assert len(candidate.citations) == 1
    assert candidate.citations[0].document_id == "doc_advisory"
    assert "CVE-2021-44228" in candidate.text
    assert "[E1]" in candidate.text
    assert "安全工具与漏洞研判发现" in candidate.text
    assert "提取安全威胁实体" in candidate.text


@pytest.mark.asyncio
async def test_cybersecurity_agent_empty_evidence() -> None:
    agent = CybersecurityAgentService()
    req = OrchestrationRequest(
        question="How to secure Kerberos?",
        actor=RequestActor(user_id="user", tenant_id="t1", role="user"),
    )
    context = ContextBundle(evidence=())
    candidate = await agent.synthesize_candidate(req, context)
    assert len(candidate.citations) == 0
    assert "本地知识库未检索到直接匹配的安全策略" in candidate.text


@pytest.mark.asyncio
async def test_cybersecurity_agent_custom_invoker() -> None:
    async def mock_invoker(prompt: str) -> str:
        assert CYBERSECURITY_SYSTEM_PROMPT in prompt
        assert "CVE-2024-3094" in prompt
        return "Specialist Model: Backdoor mitigated with [E1]."

    agent = CybersecurityAgentService(model_invoker=mock_invoker)
    req = OrchestrationRequest(
        question="Analysis for CVE-2024-3094",
        actor=RequestActor(user_id="user", tenant_id="t1", role="user"),
    )
    context = ContextBundle(
        evidence=(EvidenceItem(item_id="e1", document_id="d1", source="s1", content="Liblzma backdoor found"),)
    )
    candidate = await agent.synthesize_candidate(req, context)
    assert "Specialist Model: Backdoor mitigated with [E1]." in candidate.text
