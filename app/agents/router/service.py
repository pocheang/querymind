"""Adapt the calibrated legacy router to the immutable domain contract."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable

from app.agents.clarification.rules import assess_completeness, missing_fields
from app.core.config import get_settings
from app.domain.contracts import RouteDecision
from app.orchestration.request import OrchestrationRequest

LegacyRouteDecider = Callable[..., object]

# Explicit connector/integration commands pattern
# Matches commands like: "disable connector X", "enable integration Y", "configure connector Z"
# Supports both uppercase and lowercase connector names, and various command verbs
_EXPLICIT_CONNECTOR_COMMAND = re.compile(
    r"^\s*(?:please\s+)?"  # Optional "please"
    r"(disable|enable|configure|remove|add|setup|connect|disconnect)\s+"  # Action verbs
    r"(?:the\s+)?"  # Optional "the"
    r"(connector|integration|plugin|extension)\s+"  # Target type
    r"([a-zA-Z][a-zA-Z0-9_\-]{0,63})"  # Connector name (now allows uppercase)
    r"\s*[.!]?\s*$",  # Optional punctuation
    re.IGNORECASE,
)


class RouterAgentService:
    """Expose one asynchronous, typed route decision boundary."""

    def __init__(self, decider: LegacyRouteDecider | None = None) -> None:
        self._decider = decider or self._default_decider

    async def route(self, request: OrchestrationRequest) -> RouteDecision:
        """Delegate routing once and normalize only the public orchestration fields."""
        # Check entire question text for connector commands, not just first line
        if _EXPLICIT_CONNECTOR_COMMAND.search(request.question):
            return RouteDecision(
                intent="tool_call",
                route="react",
                confidence=1.0,
                requires_plan=True,
                allowed_capabilities=frozenset({"rag", "tool"}),
                reason="explicit_owned_connector_command",
            )
        # Assessed, but no longer short-circuiting. Returning here meant the LLM
        # router never ran for these questions, so anything that merely *looked*
        # like a comparison ("A 和 B 的区别") was answered from vector+BM25 with
        # graph and web silently excluded -- including when the user skipped
        # clarification and the pipeline continued with the original question.
        completeness = assess_completeness(request.question)
        missing = missing_fields(completeness, {})

        legacy = await asyncio.to_thread(
            self._decider,
            request.question,
            use_reasoning=request.use_reasoning,
            agent_class_hint=request.source_scope.agent_class_hint,
        )

        # Extract and validate fields from legacy router response
        try:
            # Access attributes directly - let AttributeError bubble up if missing
            route = str(legacy.route).lower() if legacy.route is not None else "vector"
            confidence = float(legacy.confidence) if legacy.confidence is not None else 0.5
            raw_confidence = float(getattr(legacy, "raw_confidence", confidence) or confidence)
            reason = str(legacy.reason) if legacy.reason is not None else "legacy_router"
            agent_class = str(getattr(legacy, "agent_class", "general") or "general")
            skill = str(getattr(legacy, "skill", "answer_with_citations") or "answer_with_citations")
        except (AttributeError, ValueError, TypeError) as exc:
            # Provide clear error message about what went wrong
            raise ValueError(
                f"Legacy router returned invalid response: {type(exc).__name__}: {exc}. "
                f"Expected object with 'route', 'confidence', and 'reason' attributes."
            ) from exc

        decision = _with_specialist_tools(
            _to_domain_route(
                route,
                confidence,
                reason,
                raw_confidence,
                agent_class=agent_class,
                skill=skill,
            )
        )
        if not missing:
            return decision
        return decision.model_copy(
            update={
                "clarification_fields": missing,
                # A question worth clarifying is a question worth planning for.
                "requires_plan": decision.requires_plan or completeness.complexity == "complex",
                "reason": f"{decision.reason}|missing_required_information:{','.join(missing)}",
            }
        )

    @staticmethod
    def _default_decider(*args: object, **kwargs: object) -> object:
        from app.agents.router.routing import decide_route

        return decide_route(*args, **kwargs)


def _with_specialist_tools(decision: RouteDecision) -> RouteDecision:
    """Let the answering specialist consult its own read-only tools.

    Only ``react`` carried the ``tool`` capability, and the router's prompt
    reserves ``react`` for multi-step reasoning -- so a question such as
    "look up the CVSS score of CVE-2022-22965" never reached the CVE lookup.
    The route itself is left as chosen: retrieval still follows it, and
    ``intent`` stays what it was, which is how the tool stage tells a
    specialist consulting its tools from a user asking for an action (see
    ``app/agents/tool/catalog.py``).

    Greetings are left alone: they need no retrieval, and no tool either.
    """

    if "tool" in decision.allowed_capabilities or "smalltalk_local_only" in decision.reason:
        return decision
    if not get_settings().specialist_tools_enabled:
        return decision
    from app.agents.tool.catalog import specialist_offers_read_tools

    if not specialist_offers_read_tools(decision.agent_class):
        return decision
    return decision.model_copy(
        update={
            "allowed_capabilities": decision.allowed_capabilities | {"tool"},
            "reason": f"{decision.reason}|specialist_tools:{decision.agent_class}",
        }
    )


def _to_domain_route(
    route: str,
    confidence: float,
    reason: str,
    raw_confidence: float | None = None,
    agent_class: str = "general",
    skill: str = "answer_with_citations",
) -> RouteDecision:
    # Warn if confidence is out of valid range before normalization
    if confidence < 0.0 or confidence > 1.0:
        import logging

        logging.getLogger(__name__).warning(
            f"Router confidence out of range [0.0, 1.0]: {confidence:.4f} for route '{route}'. "
            f"Normalizing to valid range."
        )
    normalized_confidence = min(1.0, max(0.0, confidence))
    if route == "react":
        return RouteDecision(
            intent="tool_call",
            route="react",
            confidence=normalized_confidence,
            raw_confidence=raw_confidence,
            requires_plan=True,
            allowed_capabilities=frozenset({"rag", "tool"}),
            reason=reason,
            agent_class=agent_class,
            skill=skill,
        )
    if route == "hybrid":
        return RouteDecision(
            intent="hybrid",
            route="hybrid",
            confidence=normalized_confidence,
            raw_confidence=raw_confidence,
            requires_plan=True,
            allowed_capabilities=frozenset({"rag"}),
            reason=reason,
            agent_class=agent_class,
            skill=skill,
        )
    if route == "web":
        return RouteDecision(
            intent="web_search",
            route="web",
            confidence=normalized_confidence,
            raw_confidence=raw_confidence,
            requires_plan=False,
            allowed_capabilities=frozenset({"rag", "web"}),
            reason=reason,
            agent_class=agent_class,
            skill=skill,
        )
    if route not in {"vector", "graph"}:
        raise ValueError(
            f"router returned unsupported route: {route!r} (expected: vector, graph, react, hybrid, or web)"
        )
    return RouteDecision(
        intent="knowledge_retrieval",
        route=route,
        confidence=normalized_confidence,
        raw_confidence=raw_confidence,
        requires_plan=False,
        allowed_capabilities=frozenset({"rag"}),
        reason=reason,
        agent_class=agent_class,
        skill=skill,
    )
