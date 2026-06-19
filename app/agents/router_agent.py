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
    CLASSIFICATION_HIGH_CONFIDENCE,
    CLASSIFICATION_MEDIUM_CONFIDENCE,
    ROUTE_VECTOR,
    SKILL_DEFAULT,
    VALID_AGENT_CLASSES,
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

Cyber skill hints:
- exploitation, attack chain, lateral movement, privilege escalation, C2 => cyber_attack_analysis
- defense architecture, detection rules, hardening checklist, zero trust => cyber_defense_hardening
- incident triage, containment, forensic trace, emergency drill => incident_response_playbook

PDF skill hints:
- reading PDF content, extracting text from PDF => pdf_text_reader

Output JSON only:
{"route":"vector|graph|hybrid","reason":"...","skill":"..."}
"""


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        logger.warning("No JSON found in router response, using fallback")
        return {
            "route": ROUTE_VECTOR,
            "reason": "fallback",
            "skill": SKILL_DEFAULT
        }
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error in router response: {e}")
        return {
            "route": ROUTE_VECTOR,
            "reason": "fallback_json_error",
            "skill": SKILL_DEFAULT
        }


def _normalize_agent_class_hint(agent_class_hint: str | None) -> str | None:
    """Normalize and validate agent class hint."""
    if not agent_class_hint:
        return None

    hint = normalize_string(agent_class_hint, lowercase=True)
    if hint in VALID_AGENT_CLASSES:
        return hint

    logger.debug(f"Invalid agent class hint: {agent_class_hint}")
    return None


@cached_router_decision
def decide_route(
    question: str,
    use_reasoning: bool = False,
    agent_class_hint: str | None = None,
    use_llm_intent: bool = True
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
            logger.info(
                f"LLM intent classification: {agent_class} "
                f"(confidence={confidence:.2f})"
            )
        except Exception as e:
            logger.warning(
                f"LLM intent classification failed, fallback to rule-based: {e}"
            )
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

    # Select model based on settings
    model = get_reasoning_model() if use_reasoning else get_chat_model()

    # Get route decision from LLM
    try:
        prompt = f"{ROUTER_PROMPT}\n\nQuestion: {question}\nAgent class: {agent_class}\nSuggested skill: {skill}"
        response = model.invoke(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)

        route_data = _extract_json(response_text)

        route = route_data.get("route", ROUTE_VECTOR)
        reason = route_data.get("reason", "llm_decision")
        llm_skill = route_data.get("skill", skill)

        # Use LLM skill if it looks valid
        if llm_skill and llm_skill != "...":
            skill = llm_skill

        logger.info(
            f"Route decision: route={route}, skill={skill}, "
            f"agent_class={agent_class}, method={classification_method}"
        )

    except Exception as e:
        logger.exception(f"Router LLM call failed: {e}")
        route = ROUTE_VECTOR
        reason = f"llm_error:{type(e).__name__}"

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
    else:
        agent_class = classify_agent_class(question)
        classification_method = "rule"

    forced_reason = f" | forced_agent_class={forced}" if forced else ""
    if is_smalltalk_query(question):
        return RouteDecision(
            route="vector",
            reason=f"smalltalk_local_only | agent_class={agent_class} | method={classification_method}{forced_reason}",
            skill="answer_with_citations",
            agent_class=agent_class,
        )

    try:
        model = get_reasoning_model() if use_reasoning else get_chat_model()
        result = model.invoke([("system", ROUTER_PROMPT), ("human", question)])
        text = result.content if hasattr(result, "content") else str(result)
        data = _extract_json(text)
    except Exception as e:
        data = {
            "route": "vector",
            "reason": f"router_invoke_error:{type(e).__name__}",
            "skill": "answer_with_citations",
        }

    route = data.get("route", "vector")
    reason_raw = data.get("reason", "fallback")
    if route == "web":
        reason_raw = f"{reason_raw} | web_downgraded_to_local_first"
        route = "vector"
    elif route not in {"vector", "graph", "hybrid"}:
        reason_raw = f"{reason_raw} | invalid_route_fallback_to_vector"
        route = "vector"

    skill = data.get("skill", "answer_with_citations")
    if skill not in {
        "answer_with_citations",
        "compare_entities",
        "timeline_builder",
        "web_fact_check",
        "cyber_attack_analysis",
        "cyber_defense_hardening",
        "incident_response_playbook",
        "ai_knowledge_assistant",
        "pdf_text_reader",
    }:
        skill = "answer_with_citations"

    if agent_class == "cybersecurity":
        if skill not in {"cyber_attack_analysis", "cyber_defense_hardening", "incident_response_playbook"}:
            skill = pick_cyber_skill(question)
    elif agent_class == "artificial_intelligence":
        skill = "ai_knowledge_assistant"
    elif agent_class == "pdf_text":
        if skill not in {"pdf_text_reader"}:
            skill = "pdf_text_reader"

    reason = f"{reason_raw} | agent_class={agent_class} | method={classification_method}"
    if forced:
        reason = f"{reason} | forced_agent_class={forced}"
    return RouteDecision(route=route, reason=reason, skill=skill, agent_class=agent_class)
