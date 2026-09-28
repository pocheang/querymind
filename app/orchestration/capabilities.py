"""Canonical capability assembly for typed orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.finalizer.service import FinalizationService
from app.agents.knowledge.service import KnowledgeAgentService
from app.agents.planner.service import PlannerAgentService, default_llm_decompose
from app.agents.rag.service import RAGAgentService
from app.agents.registry import DomainAgentRegistry, get_domain_agent_registry
from app.agents.router.service import RouterAgentService
from app.agents.synthesizer.service import SynthesizerAgentService
from app.agents.tool.service import ToolAgentService
from app.agents.verifier.service import VerifierAgentService
from app.orchestration.engine import OrchestrationServices
from app.privacy.service import PrivacyService


@dataclass
class CoreCapabilities:
    """Injectable canonical capabilities used by production and focused tests."""

    typed_router: RouterAgentService = field(default_factory=RouterAgentService)
    typed_knowledge: KnowledgeAgentService = field(default_factory=KnowledgeAgentService)
    typed_planner: PlannerAgentService = field(
        default_factory=lambda: PlannerAgentService(decompose=default_llm_decompose)
    )
    typed_rag: RAGAgentService = field(default_factory=RAGAgentService)
    typed_tools: ToolAgentService = field(default_factory=ToolAgentService)
    typed_synthesizer: SynthesizerAgentService = field(default_factory=SynthesizerAgentService)
    domain_agent_registry: DomainAgentRegistry = field(default_factory=get_domain_agent_registry)
    typed_verifier: VerifierAgentService = field(default_factory=VerifierAgentService)
    typed_finalizer: FinalizationService = field(default_factory=FinalizationService)
    privacy: PrivacyService = field(default_factory=PrivacyService)
    # Scope resolution and injection screening, injectable as one piece. There
    # used to be an `access_scope_resolver` field here that nothing read -- the
    # guardrail owns the resolver -- so a test injecting a resolver through it
    # silently got the default one. None builds the production guardrail.
    security_guardrail: Any = None
    context: Any = None  # Legacy context object, type varies by implementation

    def orchestration_services(self) -> OrchestrationServices:
        """Assemble orchestration services from typed capabilities.

        The event_reporter_binder allows the orchestration engine to push
        degradation events back to RAGAgentService during retrieval failures.
        """
        return OrchestrationServices(
            router=self.typed_router.route,
            planner=self.typed_planner.plan,
            retriever=self.typed_rag.retrieve,
            tool_runner=self.typed_tools.run,
            synthesizer=self.typed_synthesizer.synthesize,
            candidate_synthesizer=self.typed_synthesizer.synthesize_candidate,
            domain_agent_registry=self.domain_agent_registry,
            finalizer=self.typed_finalizer.finalize,
            verifier=self.typed_verifier.verify,
            knowledge_agent=self.typed_knowledge.decide,
            privacy=self.privacy,
            event_reporter_binder=self.typed_rag.set_degradation_reporter,
            security_guardrail=self.security_guardrail,
        )


def build_orchestration_services() -> OrchestrationServices:
    """Build the sole production capability graph without compatibility wrappers."""
    return CoreCapabilities().orchestration_services()


__all__ = ["CoreCapabilities", "build_orchestration_services"]
