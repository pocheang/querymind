"""Specialized Cybersecurity Domain Agent Service.

Responsible for:
1. Threat modeling and ATT&CK matrix alignment (Initial Access -> Exfiltration)
2. CVE vulnerability analysis and exploit mitigation guidance
3. IoC (IP, Hash, CVE) indicator extraction and correlation
4. Incident Response Playbook generation with strict citation grounding
"""

from __future__ import annotations

import re

from app.agents.base import BaseSpecialistAgent
from app.domain.contracts import ToolResult
from app.tools.category import ToolCategory

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


# A specialist skill names a shape `app/agents/synthesizer/skills.py` already
# describes. Mapping onto it rather than authoring a parallel set of templates is
# the rule that module states for itself: two competing answer shapes in one
# prompt is worse than either. Every value here is in `VALID_SKILLS`.
PIPELINE_SKILLS: dict[str, str] = {
    "cybersecurity_incident_response": "incident_response_playbook",
    "cve_vulnerability_assessment": "cyber_defense_hardening",
    "threat_intelligence_correlation": "cyber_attack_analysis",
    "cyber_attack_analysis": "cyber_attack_analysis",
}

INDICATORS_TOOL_ID = "querymind_cyber_indicator_extract"


def indicator_tool_result(iocs: dict[str, list[str]]) -> ToolResult | None:
    """The extracted IoCs, carried to the model as a TOOL finding.

    Deliberately not folded into the evidence or the rendered context: these are
    derived by a regex over material the model can already see, so presenting
    them as evidence would invite a citation pointing at a derivation rather
    than at a source. A tool observation is what they are.
    """

    lines = [f"{kind}: {', '.join(values)}" for kind, values in sorted(iocs.items()) if values]
    if not lines:
        # `ToolResult | None` rather than a 0-or-1 tuple (`python:S3800`):
        # "the finding, or nothing" is what this means, and the caller splices.
        return None
    return ToolResult(
        tool_id=INDICATORS_TOOL_ID,
        status="succeeded",
        summary="Indicators extracted from the question and retrieved material -- " + "; ".join(lines),
    )


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

    # The three things that are actually this specialist's. Everything else --
    # delegation, logging, the extraction-as-tool-finding splice, the skill
    # fallback -- lives once in `BaseSpecialistAgent`.
    pipeline_skills = PIPELINE_SKILLS
    fallback_pipeline_skill = "cyber_attack_analysis"

    def domain_findings(self, text: str) -> ToolResult | None:
        return indicator_tool_result(extract_security_indicators(text))


__all__ = [
    "CYBERSECURITY_SYSTEM_PROMPT",
    "CybersecurityAgentService",
    "PIPELINE_SKILLS",
    "extract_security_indicators",
    "indicator_tool_result",
]
