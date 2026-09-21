"""Unified Enterprise Security Guardrail Engine for QueryMind.

Integrates:
1. Anti-evasion Text De-obfuscation (Unicode NFKC, zero-width stripping, homoglyph normalization)
2. OWASP GenAI Top 10 (LLM01) Direct & Indirect Prompt Injection Defense
3. PII & Secret Redaction (DLP)
4. Multi-Tenant Access Scope Authorization
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings
from app.domain.contracts import EvidenceItem
from app.domain.knowledge import AccessScope
from app.orchestration.request import RequestActor, RequestScope
from app.privacy.models import ImageInput, PrivacyResult
from app.privacy.service import PrivacyService
from app.services.security.access_scope import AccessScopeResolver
from app.services.security.injection_defense import (
    InjectionAssessment,
    TextDeobfuscator,
    detect_prompt_injection,
    screen_evidence_items,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecurityGuardrailResult:
    """Consolidated security evaluation output for incoming workflow requests."""

    sanitized_question: str
    privacy: PrivacyResult
    permission_scope: AccessScope
    assessment: InjectionAssessment | None = None
    passed: bool = True
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class SecurityGuardrailService:
    """Unified security and safety guardrail coordinator for workflow boundaries."""

    def __init__(
        self,
        privacy_service: PrivacyService | None = None,
        access_scope_resolver: AccessScopeResolver | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._privacy = privacy_service or PrivacyService()
        self._access_scope_resolver = access_scope_resolver or AccessScopeResolver()
        self._settings = settings or get_settings()

    @property
    def privacy(self) -> PrivacyService:
        return self._privacy

    @property
    def access_scope_resolver(self) -> AccessScopeResolver:
        return self._access_scope_resolver

    def inspect_and_authorize(
        self,
        question: str,
        actor: RequestActor,
        source_scope: RequestScope | None = None,
        images: Sequence[ImageInput] = (),
    ) -> SecurityGuardrailResult:
        """Execute full defense-in-depth preflight check:

        1. Clean and normalize anti-evasion text
        2. Detect and intercept Prompt Injections / Jailbreaks
        3. Inspect and redact PII / Secrets
        4. Resolve caller tenant & document access scope
        """
        raw_text = str(question or "")
        cleaned_text = TextDeobfuscator.clean(raw_text)

        # 1. Prompt Injection Defense (OWASP LLM01 / NIST AI RMF)
        assessment: InjectionAssessment | None = None
        defense_enabled = bool(getattr(self._settings, "prompt_injection_defense_enabled", True))
        if defense_enabled and cleaned_text:
            assessment = detect_prompt_injection(cleaned_text, is_retrieved_evidence=False)
            if assessment.is_blocked:
                threat_name = assessment.threat_type.value if assessment.threat_type else "injection_threat"
                logger.warning(
                    "SecurityGuardrail blocked input: threat=%s risk=%.2f rules=%s",
                    threat_name,
                    assessment.risk_score,
                    assessment.matched_rules,
                )
                raise PermissionError(
                    f"security guardrail blocked request: prompt injection threat detected ({threat_name})"
                )

        # 2. Privacy & PII / Secret Inspection
        privacy_result = self._privacy.inspect_input(cleaned_text or raw_text, images=images)
        if privacy_result.blocked:
            logger.warning("SecurityGuardrail blocked input: privacy inspection failed")
            raise PermissionError("security guardrail blocked request: input privacy inspection blocked")

        # 3. Access Scope Authorization
        scope = self._access_scope_resolver.resolve(actor, source_scope)

        return SecurityGuardrailResult(
            sanitized_question=privacy_result.text,
            privacy=privacy_result,
            permission_scope=scope,
            assessment=assessment,
            passed=True,
            reason="authorized",
        )

    def inspect_evidence(self, items: Sequence[EvidenceItem]) -> tuple[EvidenceItem, ...]:
        """Inspect retrieved evidence chunks for Indirect Prompt Injections (IPI).

        Delegates to `screen_evidence_items`, which is also what
        `ContextBuilder.build` calls. Two implementations of "what counts as a
        poisoned chunk" is how the two drift, and the live path is the builder:
        this method is the service-level entry point for callers that already
        hold a guardrail.
        """

        return screen_evidence_items(items)


__all__ = ["SecurityGuardrailResult", "SecurityGuardrailService"]
