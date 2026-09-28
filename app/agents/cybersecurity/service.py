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
from app.agents.catalog import AgentClass
from app.domain.contracts import ToolResult
from app.services.query.keyword_match import any_keyword
from app.tools.category import ToolCategory

# There is no domain system prompt here. One was written and exported and nothing
# ever read it -- generation goes through `SynthesizerAgentService`, whose skill
# templates are where answer guidance lives -- so it was deleted rather than
# wired in: a second instruction block would compete with the template.

# An octet is 0-255, and an address is not the middle of a longer dotted run:
# `\d{1,3}` accepted 999.1.1.1, and `\b` let a version string such as 1.2.3.4.5
# contribute its first four parts. The lookahead refuses a further `.digit`
# rather than any `.`, so an address that ends a sentence is still found.
_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_IP_RE = re.compile(rf"(?<![\d.]){_OCTET}(?:\.{_OCTET}){{3}}(?!\.?\d)")
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
# MD5, SHA-1 and SHA-256 are 32, 40 and 64 hex characters. `{32,64}` also took
# every length in between, which no digest has.
_HASH_RE = re.compile(r"\b(?:[a-f0-9]{64}|[a-f0-9]{40}|[a-f0-9]{32})\b", re.IGNORECASE)


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


_RESPONSE_KEYWORDS = ("应急", "处置", "隔离", "溯源", "恢复", "止损", "playbook", "incident response")
_ASSESSMENT_KEYWORDS = ("cve", "补丁", "修复", "版本", "影响范围", "受影响", "patch", "affected")


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
        derived=True,
        summary="Indicators extracted from the question and retrieved material -- " + "; ".join(lines),
    )


class CybersecurityAgentService(BaseSpecialistAgent):
    """Specialist agent for cybersecurity queries."""

    @property
    def agent_class(self) -> str:
        return AgentClass.CYBERSECURITY

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
            # Prompt injection is an attack on the application, not a question
            # about models. Named in full: a bare "注入" would also claim
            # "依赖注入", which is a software-design question.
            "提示词注入",
            "prompt注入",
            "prompt 注入",
            "prompt injection",
            "注入攻击",
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
        """Response first, then assessment; attack analysis otherwise.

        The order is the point. "漏洞"/"cve" used to be tested first, so every
        question naming a CVE became attack analysis -- including
        "CVE-2021-44228 漏洞应急处置步骤", which asks for a playbook -- and
        `cve_vulnerability_assessment` could only be reached by a question that
        named no CVE at all. A question that asks how to respond wants the
        response; the CVE is its subject, not its shape.

        Attack wording needs no branch of its own: attack analysis is also the
        fallback, so testing for it would return what not testing returns.
        """

        if any_keyword(question, _RESPONSE_KEYWORDS):
            return "cybersecurity_incident_response"
        if any_keyword(question, _ASSESSMENT_KEYWORDS):
            return "cve_vulnerability_assessment"
        return "cyber_attack_analysis"

    # The three things that are actually this specialist's. Everything else --
    # delegation, logging, the extraction-as-tool-finding splice, the skill
    # fallback -- lives once in `BaseSpecialistAgent`.
    pipeline_skills = PIPELINE_SKILLS
    fallback_pipeline_skill = "cyber_attack_analysis"

    def domain_findings(self, text: str) -> ToolResult | None:
        return indicator_tool_result(extract_security_indicators(text))


__all__ = [
    "CybersecurityAgentService",
    "PIPELINE_SKILLS",
    "extract_security_indicators",
    "indicator_tool_result",
]
