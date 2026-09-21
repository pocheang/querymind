"""Clarification Agent: gather missing fields and compose one complete query."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
from typing import Any

from app.agents.clarification.prompts import build_clarification_prompt
from app.agents.clarification.rules import (
    assess_completeness,
    max_rounds_for,
    missing_fields,
    question_for,
)
from app.core.config import get_settings, resolve_response_signing_secret
from app.domain.contracts import ClarificationContext, ClarificationQuestion
from app.domain.workflow import ClarificationResult, RouterDecision
from app.orchestration.request import OrchestrationRequest
from app.services.models.runtime import get_chat_model
from app.services.query.intent import is_smalltalk_query

logger = logging.getLogger(__name__)

_OTHER_OPTION_ZH = "其他（自定义输入 / 补充说明）"
_OTHER_OPTION_EN = "Other (Custom input / specify details)"
_VALID_FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ClarificationAgentService:
    """Dual-track clarification boundary: deterministic fast-path rules + dynamic LLM evaluation."""

    def clarify(
        self,
        request: OrchestrationRequest,
        route: RouterDecision | None = None,
        *,
        context: ClarificationContext | None = None,
        workflow_thread_id: str | None = None,
    ) -> ClarificationResult:
        """Synchronous clarification boundary (fast-path rules + synchronous dynamic LLM evaluation)."""
        del route
        active_context, thread_id = self._prepare_context(request, context, workflow_thread_id)

        # Track 1: Fast-path deterministic rule matching
        rule_result = self._rule_based_clarification(request, active_context, thread_id)
        if rule_result is not None:
            return rule_result

        # Track 2: Dynamic LLM clarification evaluation
        return self._evaluate_dynamic_clarification(request, active_context, thread_id)

    async def a_clarify(
        self,
        request: OrchestrationRequest,
        route: RouterDecision | None = None,
        *,
        context: ClarificationContext | None = None,
        workflow_thread_id: str | None = None,
    ) -> ClarificationResult:
        """Asynchronous clarification boundary (fast-path rules + asynchronous dynamic LLM evaluation)."""
        del route
        active_context, thread_id = self._prepare_context(request, context, workflow_thread_id)

        # Track 1: Fast-path deterministic rule matching
        rule_result = self._rule_based_clarification(request, active_context, thread_id)
        if rule_result is not None:
            return rule_result

        # Track 2: Dynamic LLM clarification evaluation (non-blocking)
        return await self._a_evaluate_dynamic_clarification(request, active_context, thread_id)

    def _prepare_context(
        self,
        request: OrchestrationRequest,
        context: ClarificationContext | None,
        workflow_thread_id: str | None,
    ) -> tuple[ClarificationContext, str]:
        active_context = (context or ClarificationContext()).model_copy(deep=True)
        if active_context.original_query and active_context.original_query != request.question:
            active_context = ClarificationContext(original_query=request.question)
        elif not active_context.original_query:
            active_context.original_query = request.question
        thread_id = workflow_thread_id or self.workflow_thread_id(request)
        return active_context, thread_id

    def _rule_based_clarification(
        self,
        request: OrchestrationRequest,
        active_context: ClarificationContext,
        thread_id: str,
    ) -> ClarificationResult | None:
        """Evaluate deterministic rules from rules.py. Returns None if intent is 'complete'."""
        assessment = assess_completeness(request.question)
        if assessment.intent == "complete":
            return None

        active_context.intent = assessment.intent
        active_context.max_rounds = max_rounds_for(assessment.intent)
        missing = missing_fields(assessment, active_context.collected_info)

        if not missing or active_context.clarification_round >= active_context.max_rounds:
            return ClarificationResult(
                action="continue",
                context=active_context,
                complete_query=self.compose_complete_query(request.question, active_context.collected_info),
                workflow_thread_id=thread_id,
            )

        next_field = next(
            (field_name for field_name in missing if field_name not in active_context.asked_questions),
            None,
        )
        question = question_for(
            assessment.intent,
            next_field or "",
            language=_question_language(request),
        )
        if question is None:
            return ClarificationResult(
                action="continue",
                context=active_context,
                complete_query=self.compose_complete_query(request.question, active_context.collected_info),
                workflow_thread_id=thread_id,
            )

        asked = active_context.asked_questions
        active_context = active_context.model_copy(
            update={
                "clarification_round": active_context.clarification_round + 1,
                "asked_questions": [*asked, next_field] if next_field and next_field not in asked else asked,
            }
        )
        return ClarificationResult(
            action="ask",
            question=question,
            context=active_context,
            workflow_thread_id=thread_id,
        )

    def _evaluate_dynamic_clarification(
        self,
        request: OrchestrationRequest,
        active_context: ClarificationContext,
        thread_id: str,
    ) -> ClarificationResult:
        """Evaluate vague queries with LLM synchronously."""
        if self._should_skip_dynamic(request, active_context):
            return self._continue_result(request.question, active_context, thread_id)

        prompt = self._build_prompt(request, active_context)
        try:
            model = get_chat_model(temperature=0.0)
            response = model.invoke([("system", prompt)])
            eval_data = _extract_json(getattr(response, "content", ""))
            if eval_data:
                return self._process_eval_data(eval_data, request, active_context, thread_id)
        except Exception as err:
            logger.warning("Synchronous dynamic clarification failed, continuing safely: %s", err)

        return self._continue_result(request.question, active_context, thread_id)

    async def _a_evaluate_dynamic_clarification(
        self,
        request: OrchestrationRequest,
        active_context: ClarificationContext,
        thread_id: str,
    ) -> ClarificationResult:
        """Evaluate vague queries with LLM asynchronously."""
        if self._should_skip_dynamic(request, active_context):
            return self._continue_result(request.question, active_context, thread_id)

        prompt = self._build_prompt(request, active_context)
        try:
            model = get_chat_model(temperature=0.0)
            if hasattr(model, "ainvoke"):
                response = await model.ainvoke([("system", prompt)])
            else:
                response = await asyncio.to_thread(model.invoke, [("system", prompt)])
            eval_data = _extract_json(getattr(response, "content", ""))
            if eval_data:
                return self._process_eval_data(eval_data, request, active_context, thread_id)
        except Exception as err:
            logger.warning("Asynchronous dynamic clarification failed, continuing safely: %s", err)

        return self._continue_result(request.question, active_context, thread_id)

    def _should_skip_dynamic(self, request: OrchestrationRequest, active_context: ClarificationContext) -> bool:
        if is_smalltalk_query(request.question):
            return True
        max_dynamic_rounds = min(active_context.max_rounds, 3)
        return active_context.clarification_round >= max_dynamic_rounds

    def _build_prompt(self, request: OrchestrationRequest, active_context: ClarificationContext) -> str:
        return build_clarification_prompt(
            question=request.question,
            collected_info=active_context.collected_info,
            asked_questions=active_context.asked_questions,
            language=_question_language(request),
        )

    def _process_eval_data(
        self,
        eval_data: dict[str, Any],
        request: OrchestrationRequest,
        active_context: ClarificationContext,
        thread_id: str,
    ) -> ClarificationResult:
        if not eval_data.get("needs_clarification"):
            return self._continue_result(request.question, active_context, thread_id)

        field_name = _clean_field_name(str(eval_data.get("field_name") or ""))
        question_text = str(eval_data.get("question") or "").strip()
        raw_options = eval_data.get("options")
        options = _normalize_options(
            raw_options if isinstance(raw_options, list) else [],
            _question_language(request),
        )

        if not question_text or field_name in active_context.asked_questions:
            return self._continue_result(request.question, active_context, thread_id)

        question = ClarificationQuestion(
            question=question_text,
            options=options,
            allow_custom_input=True,
            field_name=field_name,
        )

        asked = active_context.asked_questions
        active_context = active_context.model_copy(
            update={
                "clarification_round": active_context.clarification_round + 1,
                "asked_questions": [*asked, field_name],
                "intent": f"dynamic_{field_name}",
                "max_rounds": min(active_context.max_rounds, 3),
            }
        )
        return ClarificationResult(
            action="ask",
            question=question,
            context=active_context,
            workflow_thread_id=thread_id,
        )

    def _continue_result(
        self,
        question: str,
        active_context: ClarificationContext,
        thread_id: str,
    ) -> ClarificationResult:
        return ClarificationResult(
            action="continue",
            context=active_context,
            complete_query=self.compose_complete_query(question, active_context.collected_info),
            workflow_thread_id=thread_id,
        )

    @staticmethod
    def compose_complete_query(original_query: str, collected_info: dict[str, str]) -> str:
        """Render confirmed fields without changing the user's original wording."""
        original = str(original_query or "").strip()
        confirmed = sorted(
            (str(key).strip(), str(value).strip())
            for key, value in collected_info.items()
            if str(key).strip() and str(value).strip()
        )
        if not confirmed:
            return original
        lines = [original, "", "Confirmed constraints:"]
        lines.extend(f"- {key}: {value}" for key, value in confirmed)
        return "\n".join(lines)

    @staticmethod
    def workflow_thread_id(request: OrchestrationRequest) -> str:
        actor = request.actor
        tenant_id = str((actor.tenant_id if actor else None) or (actor.user_id if actor else None) or "anonymous")
        user_id = str((actor.user_id if actor else None) or "anonymous")
        session_id = str(request.session_id or request.request_id or request.execution_id or "request-local")
        return ":".join((tenant_id, user_id, session_id))

    @staticmethod
    def issue_resume_token(workflow_thread_id: str) -> str | None:
        """Sign a correlation token when the existing response-signing key is configured."""
        _kid, secret = resolve_response_signing_secret(get_settings())
        if not secret:
            return None
        return hmac.new(secret.encode("utf-8"), workflow_thread_id.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def resume_token_is_valid(cls, workflow_thread_id: str, token: str | None) -> bool:
        expected = cls.issue_resume_token(workflow_thread_id)
        if expected is None:
            return token is None
        return bool(token) and hmac.compare_digest(expected, str(token))


def _question_language(request: OrchestrationRequest) -> str:
    """Pick the clarification language from explicit override, then query text."""
    forced = str(getattr(request, "force_language", "") or "").strip().lower()
    if forced in {"zh", "en"}:
        return forced
    return "zh" if any("一" <= ch <= "鿿" for ch in str(request.question or "")) else "en"


def _clean_field_name(raw_name: str) -> str:
    """Normalize dynamic field name to match ^[a-z][a-z0-9_]{0,63}$."""
    clean = re.sub(r"[^a-z0-9_]", "_", str(raw_name or "").lower().strip())
    clean = re.sub(r"_+", "_", clean).strip("_")
    if not clean or not clean[0].isalpha():
        clean = f"field_{clean}" if clean else "field_requirement"
    clean = clean[:64]
    return clean if _VALID_FIELD_NAME_RE.match(clean) else "field_requirement"


def _normalize_options(raw_options: list[Any], language: str) -> list[str]:
    """Ensure options strictly follow Codex/Claude Code standards:

    - First option prefixed with (推荐) or (Recommended)
    - Last option is Other (Custom input / specify details)
    - 2-5 options total
    """
    is_zh = language == "zh"
    other_label = _OTHER_OPTION_ZH if is_zh else _OTHER_OPTION_EN
    rec_tag = "(推荐)" if is_zh else "(Recommended)"

    candidates = [str(opt).strip() for opt in raw_options if str(opt).strip() and str(opt).strip() != other_label]

    if candidates:
        first_opt = candidates[0]
        if not first_opt.startswith(rec_tag):
            candidates[0] = f"{rec_tag} {first_opt}".strip()
        result = candidates[:4]
    elif is_zh:
        result = [
            f"{rec_tag} 优先采用轻量模块化方案：便于快速迭代与渐进式演进",
            "企业级标准化架构：兼顾多团队协作与高可用规范",
        ]
    else:
        result = [
            f"{rec_tag} Lightweight modular approach: Best for rapid evolution and maintenance",
            "Enterprise standard architecture: Prioritizing high availability and scale",
        ]

    result.append(other_label)
    return result


def _extract_json(content: str) -> dict[str, Any] | None:
    """Extract and parse JSON safely from model response."""
    text = str(content or "").strip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace == -1 or last_brace <= first_brace:
        return None

    candidate = text[first_brace : last_brace + 1]
    # Fix common unicode quote issues
    candidate = candidate.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    try:
        data = json.loads(candidate)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


__all__ = ["ClarificationAgentService"]
