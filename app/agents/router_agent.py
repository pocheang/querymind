"""
Router Agent - Query routing and skill selection.

Optimizations:
- Uses centralized configuration
- Caching for router decisions
- Improved type hints and error handling
- Better logging and diagnostics
"""

import json
import logging
import re

from pydantic import BaseModel

from app.agents.agent_config import (
    AGENT_CLASS_GENERAL,
    ROUTE_VECTOR,
    ROUTE_WEB,
    SKILL_DEFAULT,
    VALID_AGENT_CLASSES,
    VALID_ROUTES,
    VALID_SKILLS,
)
from app.agents.shared_cache import cached_router_decision
from app.api.utils.string_utils import normalize_string
from app.core.models import get_chat_model, get_reasoning_model
from app.services.agent_classifier import classify_agent_class, pick_cyber_skill
from app.services.llm_intent_classifier import classify_intent_with_llm
from app.services.query_intent import is_smalltalk_query

logger = logging.getLogger(__name__)


class RouteDecision(BaseModel):
    """Router decision with route, skill, and agent class."""

    route: str
    reason: str
    skill: str
    agent_class: str


ROUTER_PROMPT = """
You are a route planner for a cybersecurity RAG assistant.

Choose one route:
- vector: best for finding answers from text chunks
- graph: best for entity relations, dependencies, and topology
- hybrid: needs both text evidence and relation graph
- react: complex multi-step queries requiring iterative reasoning and tool use

Choose one skill from:
- answer_with_citations
- compare_entities
- timeline_builder
- web_fact_check
- cyber_attack_analysis
- cyber_defense_hardening
- incident_response_playbook
- ai_knowledge_assistant
- pdf_text_reader

ReAct route hints:
- Multi-step reasoning: "compare X and Y, then analyze Z"
- Complex questions requiring multiple information sources
- Questions needing sequential tool calls: search, verify, synthesize
- Investigative queries: "find X, check if Y, recommend Z"

Cyber skill hints:
- exploitation, attack chain, lateral movement, privilege escalation, C2 => cyber_attack_analysis
- defense architecture, detection rules, hardening checklist, zero trust => cyber_defense_hardening
- incident triage, containment, forensic trace, emergency drill => incident_response_playbook

PDF skill hints:
- reading PDF content, extracting text from PDF => pdf_text_reader

Output JSON only:
{"route":"vector|graph|hybrid|react","reason":"...","skill":"..."}
"""


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        logger.warning("No JSON found in router response, using fallback")
        return {"route": ROUTE_VECTOR, "reason": "fallback", "skill": SKILL_DEFAULT}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error in router response: {e}")
        return {"route": ROUTE_VECTOR, "reason": "fallback_json_error", "skill": SKILL_DEFAULT}


def _normalize_agent_class_hint(agent_class_hint: str | None) -> str | None:
    """Normalize and validate agent class hint."""
    if not agent_class_hint:
        return None

    hint = normalize_string(agent_class_hint, lowercase=True)
    if hint in VALID_AGENT_CLASSES:
        return hint

    logger.debug(f"Invalid agent class hint: {agent_class_hint}")
    return None


def _append_reason(base_reason: str, *tags: str) -> str:
    """Join a base reason with optional diagnostic tags."""
    parts = [normalize_string(base_reason)]
    parts.extend(normalize_string(tag) for tag in tags if normalize_string(tag))
    return "|".join(part for part in parts if part)


@cached_router_decision
def decide_route(
    question: str, use_reasoning: bool = False, agent_class_hint: str | None = None, use_llm_intent: bool = True
) -> RouteDecision:
    """
    Decide query route and skill.

    This function is cached - identical queries will return cached decisions.

    Args:
        question: User question
        use_reasoning: Whether to use reasoning model
        agent_class_hint: Force specific agent class
        use_llm_intent: Use LLM for intent classification (default True)

    Returns:
        RouteDecision: Route decision with route, skill, and agent class
    """
    forced = _normalize_agent_class_hint(agent_class_hint)

    if is_smalltalk_query(question):
        return RouteDecision(
            route=ROUTE_VECTOR,
            reason=_append_reason(
                "smalltalk_local_only",
                f"forced_agent_class={forced}" if forced else "",
            ),
            skill=SKILL_DEFAULT,
            agent_class=forced or AGENT_CLASS_GENERAL,
        )

    # Select intent classification method
    if forced:
        agent_class = forced
        classification_method = "forced"
        confidence = 1.0
    elif use_llm_intent:
        try:
            intent_result = classify_intent_with_llm(question)
            agent_class = intent_result["agent_class"]
            confidence = intent_result.get("confidence", 0.5)
            classification_method = f"llm(confidence={confidence:.2f})"
            logger.info(f"LLM intent classification: {agent_class} (confidence={confidence:.2f})")
        except Exception as e:
            logger.warning(f"LLM intent classification failed, fallback to rule-based: {e}")
            agent_class = classify_agent_class(question)
            confidence = 0.5
            classification_method = "rule_fallback"
    else:
        agent_class = classify_agent_class(question)
        confidence = 0.5
        classification_method = "rule_based"

    # Determine skill based on agent class and question
    if agent_class == "cybersecurity":
        skill = pick_cyber_skill(question)
    elif agent_class == "pdf_text":
        skill = "pdf_text_reader"
    elif "compare" in question.lower() or "difference" in question.lower():
        skill = "compare_entities"
    elif "timeline" in question.lower() or "history" in question.lower():
        skill = "timeline_builder"
    else:
        skill = SKILL_DEFAULT

    forced_reason = f"forced_agent_class={forced}" if forced else ""

    # Get route decision from LLM
    try:
        model = get_reasoning_model() if use_reasoning else get_chat_model()
        prompt = f"""{ROUTER_PROMPT}

Question: {question}
Agent class: {agent_class}
Suggested skill: {skill}"""
        response = model.invoke(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)

        route_data = _extract_json(response_text)

        raw_route = normalize_string(route_data.get("route", ROUTE_VECTOR), lowercase=True)
        route = raw_route if raw_route in VALID_ROUTES else ROUTE_VECTOR

        reason = normalize_string(route_data.get("reason", "llm_decision")) or "llm_decision"
        if raw_route and raw_route not in VALID_ROUTES:
            reason = _append_reason(reason, f"invalid_route={raw_route}")

        llm_skill = normalize_string(route_data.get("skill", skill), lowercase=True)
        if llm_skill and llm_skill != "...":
            if llm_skill in VALID_SKILLS:
                skill = llm_skill
            else:
                reason = _append_reason(reason, f"invalid_skill={llm_skill}")
                # Keep the pre-determined skill (don't override with invalid value)

        if route == ROUTE_WEB:
            route = ROUTE_VECTOR
            reason = _append_reason(reason, "web_downgraded_to_local_first")

        if forced_reason:
            reason = _append_reason(reason, forced_reason)

        logger.info(
            f"Route decision: route={route}, skill={skill}, "
            f"agent_class={agent_class}, method={classification_method}, "
            f"confidence={confidence:.2f}"
        )

    except Exception as e:
        logger.exception(f"Router LLM call failed: {e}")
        route = ROUTE_VECTOR
        reason = _append_reason(f"router_invoke_error:{type(e).__name__}", forced_reason)

    return RouteDecision(
        route=route,
        reason=reason,
        skill=skill,
        agent_class=agent_class,
    )


def decide_route_simple(question: str) -> str:
    """
    Simple route decision without full skill selection.

    Args:
        question: User question

    Returns:
        Route name ("vector", "graph", "hybrid")
    """
    decision = decide_route(question, use_llm_intent=False)
    return decision.route
