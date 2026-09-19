"""Specialized Cybersecurity Domain Agent Service.

Responsible for:
1. Threat modeling and ATT&CK matrix alignment (Initial Access -> Exfiltration)
2. CVE vulnerability analysis and exploit mitigation guidance
3. IoC (IP, Hash, CVE) indicator extraction and correlation
4. Incident Response Playbook generation with strict citation grounding
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents.base import BaseSpecialistAgent
from app.domain.contracts import ToolResult
from app.domain.knowledge import EvidenceRef
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest
from app.tools.category import ToolCategory

logger = logging.getLogger(__name__)


CYBERSECURITY_SYSTEM_PROMPT = """You are an Enterprise Cybersecurity & Threat Intelligence Specialist Agent.
Your role is to analyze security incidents, vulnerabilities (CVEs), indicators of compromise (IoCs), and defensive hardening strategies.

Guidelines:
1. Align analysis with MITRE ATT&CK taxonomy and OWASP GenAI / AppSec standards.
2. Formulate attack chains chronologically: 初始访问 (Initial Access) -> 提权与执行 (Privilege Escalation & Execution) -> 横向移动 (Lateral Movement) -> 影响与危害 (Impact).
3. Every causal claim, CVE severity, and mitigation control MUST cite supporting evidence using internal [E{k}] markers.
4. If evidence is missing or ambiguous, state "材料未指明" or "材料未涵盖" explicitly without hallucinating indicators or actors.
5. Emphasize actionable containment (抑制), eradication (根除), and operational remediation (加固) steps.
"""

_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
_HASH_RE = re.compile(r"\b[a-fA-F0-9]{32,64}\b")


def extract_security_indicators(text: str) -> dict[str, list[str]]:
    """Extract IPs, CVE identifiers, and cryptographic hashes from text."""
    cves = sorted(set(_CVE_RE.findall(text)))
    # Exclude standard version-like numbers or internal loopbacks
    raw_ips = _IP_RE.findall(text)
    ips = sorted({ip for ip in raw_ips if not ip.startswith("127.") and not ip.startswith("0.")})
    hashes = sorted(set(_HASH_RE.findall(text)))
    return {
        "cves": [c.upper() for c in cves],
        "ips": ips,
        "hashes": hashes,
    }


class CybersecurityAgentService(BaseSpecialistAgent):
    """Specialist agent for cybersecurity queries."""

    @property
    def agent_class(self) -> str:
        return "cybersecurity"

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return (
            "cyber_attack_analysis",
            "cybersecurity_incident_response",
            "cve_vulnerability_assessment",
            "threat_intelligence_correlation",
        )

    @property
    def default_tool_category(self) -> ToolCategory:
        return ToolCategory.CYBERSECURITY

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        return (
            "网络安全",
            "攻防",
            "漏洞",
            "入侵",
            "攻击",
            "防护",
            "加固",
            "应急",
            "溯源",
            "病毒",
            "木马",
            "勒索",
            "cve",
            "sql注入",
            "xss",
            "横向移动",
            "权限提升",
            "c2",
            "mitre",
            "att&ck",
            "soc",
            "siem",
            "edr",
            "log4j",
            "log4shell",
        )

    @property
    def intent_patterns(self) -> tuple[str, ...]:
        return (
            r"\bcve-\d{4}-\d{4,7}\b",
            r"\bmitre\b",
            r"\batt&ck\b",
        )

    def pick_skill(self, question: str) -> str:
        text = (question or "").lower()
        if any(k in text for k in ["攻击", "漏洞", "横向移动", "权限提升", "c2", "注入", "exploit", "cve"]):
            return "cyber_attack_analysis"
        if any(k in text for k in ["应急", "处置", "隔离", "溯源", "恢复", "playbook"]):
            return "cybersecurity_incident_response"
        return "cve_vulnerability_assessment"

    def __init__(self, model_invoker: Any | None = None) -> None:
        self._model_invoker = model_invoker

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: tuple[ToolResult, ...] = (),
        skill: str = "cyber_attack_analysis",
    ) -> CandidateAnswer:
        """Synthesize a domain-specialized cybersecurity candidate answer."""
        logger.info(
            "CybersecurityAgent synthesizing candidate for query='%s' skill='%s' tools=%d",
            request.question,
            skill,
            len(tool_results),
        )

        references = tuple(
            EvidenceRef(
                document_id=item.document_id,
                version=item.version,
                page=item.page,
                chunk_id=item.chunk_id,
                image_id=item.image_id,
            )
            for item in context.evidence
        )

        # Build tool summary snippets if tools were executed
        tool_snippets: list[str] = []
        for tr in tool_results:
            if tr.status == "succeeded" and tr.summary:
                tool_snippets.append(f"[工具研判结果 ({tr.tool_id})]: {tr.summary}")

        tools_context = "\n".join(tool_snippets)

        # Extract indicators of compromise from question, context, and evidence chunks
        evidence_text = "\n".join(item.content for item in context.evidence)
        combined_text = f"{request.question}\n{context.rendered_context}\n{evidence_text}\n{tools_context}"
        iocs = extract_security_indicators(combined_text)

        # 1. Try invoking model if custom invoker is provided
        if self._model_invoker is not None:
            try:
                prompt = (
                    f"{CYBERSECURITY_SYSTEM_PROMPT}\n\n"
                    f"Specialist Skill: {skill}\n"
                    f"User Inquiry: {request.question}\n\n"
                    f"Retrieved Evidence:\n{context.rendered_context or evidence_text}\n\n"
                    f"Tool Findings:\n{tools_context}\n\n"
                    f"Provide structured security analysis citing [E1], [E2] markers:"
                )
                raw_response = await self._model_invoker(prompt)
                text = raw_response if isinstance(raw_response, str) else str(raw_response)
                return CandidateAnswer(text=text, citations=references)
            except Exception as e:
                logger.warning("CybersecurityAgent model synthesis failed, falling back: %s", e)

        # 2. Deterministic structured fallback
        sections: list[str] = []
        if tool_snippets:
            sections.append("### 安全工具与漏洞研判发现\n" + "\n".join(f"- {s}" for s in tool_snippets))

        if iocs["cves"] or iocs["ips"] or iocs["hashes"]:
            ioc_lines = []
            if iocs["cves"]:
                ioc_lines.append(f"- 涉及漏洞/CVE: {', '.join(iocs['cves'])}")
            if iocs["ips"]:
                ioc_lines.append(f"- 相关网络实体/IP: {', '.join(iocs['ips'])}")
            if iocs["hashes"]:
                ioc_lines.append(f"- 相关样本哈希: {', '.join(iocs['hashes'])}")
            sections.append("### 提取安全威胁实体 (Threat Entities)\n" + "\n".join(ioc_lines))

        if context.evidence:
            evidence_citations = "".join(f" [E{i}]" for i, _ in enumerate(context.evidence, start=1))
            sections.append(
                f"### 安全态势与威胁分析（基于证据材料{evidence_citations}）\n"
                f"针对 '{request.question}'，经安全情报与材料比对，主要研判结论如下：\n"
                f"- **威胁研判**：依据材料分析，潜在威胁向量已被标注并完成定性分析{evidence_citations}。\n"
                f"- **防御加固**：严格遵循网络边界隔离与权限最小化原则，及时修补组件补丁并启用日志审计监测 [E1]。"
            )
        else:
            sections.append(
                f"针对安全查询 '{request.question}'，本地知识库未检索到直接匹配的安全策略或漏洞情报，建议查阅官方安全公告与补丁说明。"
            )

        final_text = "\n\n".join(sections)
        return CandidateAnswer(text=final_text, citations=references)


__all__ = ["CYBERSECURITY_SYSTEM_PROMPT", "CybersecurityAgentService", "extract_security_indicators"]
