"""`OrchestrationServices` takes named parameters, not a kwargs bag.

The specialist-agent change replaced the typed `event_reporter_binder`
parameter with `**extra_services: Any` and read the new services out of it with
`.get()`. Measured on that form, `event_reporter_bindr=<callable>` -- one letter
wrong -- was accepted silently and the binder stayed `None`: a request's event
reporter would simply never be installed, with nothing anywhere reporting it.

This repository already states the opposite rule for `owner` on the retrieval
path: keyword-only with no default, "so omitting it is a `TypeError` rather than
a silent widening". A kwargs bag on the services container is that rule
inverted, and it is worse here than on a helper, because every one of these
parameters is a seam something security-relevant hangs off.
"""

from __future__ import annotations

import inspect

import pytest

from app.orchestration.engine import OrchestrationServices
from app.services.security.security_guardrail import SecurityGuardrailService


def _noop(*args: object, **kwargs: object) -> None:
    return None


def _services(**overrides: object) -> OrchestrationServices:
    base: dict[str, object] = {
        "router": _noop,
        "planner": _noop,
        "retriever": _noop,
        "tool_runner": _noop,
        "synthesizer": _noop,
        "verifier": _noop,
    }
    base.update(overrides)
    return OrchestrationServices(**base)  # type: ignore[arg-type]


def test_an_unknown_keyword_is_refused():
    """The assertion the kwargs bag could not make."""

    with pytest.raises(TypeError):
        _services(event_reporter_bindr=_noop)


def test_the_signature_declares_no_var_keyword():
    """Asserted on the signature as well as on the behaviour, because a bag that
    validated its keys by hand would pass the test above and still invite the
    next service to be added untyped."""

    params = inspect.signature(OrchestrationServices.__init__).parameters
    kinds = {name: p.kind for name, p in params.items()}

    assert inspect.Parameter.VAR_KEYWORD not in kinds.values()
    for name in ("domain_agent_registry", "security_guardrail"):
        assert kinds[name] is inspect.Parameter.KEYWORD_ONLY, f"{name} must be a named keyword-only parameter"


def test_the_binder_is_installed_when_it_is_spelled_correctly():
    """The direction that makes the refusal meaningful: the parameter still
    works, so the test above is not passing because nothing is wired."""

    binder = _noop
    assert _services(event_reporter_binder=binder)._event_reporter_binder is binder


def test_a_guardrail_is_always_present():
    """Never `None`. `privacy_permission` reaches it by plain attribute access,
    so an absent guardrail must be impossible to construct rather than quietly
    selecting a path that runs no prompt-injection screening at all."""

    assert isinstance(_services().security_guardrail, SecurityGuardrailService)


def test_an_injected_guardrail_is_the_one_used():
    """And the resolver comes from it.

    `access_scope_resolver` is no longer a parameter of its own: the guardrail
    owns scope resolution and exposes it, and two ways to supply the same
    resolver is how the two come to differ.
    """

    class _Guardrail:
        access_scope_resolver = object()

    guardrail = _Guardrail()
    services = _services(security_guardrail=guardrail)

    assert services.security_guardrail is guardrail
    assert services.access_scope_resolver is _Guardrail.access_scope_resolver


def test_the_named_specialist_parameters_are_gone():
    """The registry is the one source of specialists.

    `cybersecurity_agent` and `ai_agent` sat beside `domain_agent_registry`,
    filled from separate `CoreCapabilities` fields, so a deployment held two
    instances of each and which one answered depended on whether the registry
    lookup hit. Asserted as an absence so they cannot come back one at a time.
    """

    params = inspect.signature(OrchestrationServices.__init__).parameters

    assert "cybersecurity_agent" not in params
    assert "ai_agent" not in params
    assert "domain_agent_registry" in params


@pytest.mark.asyncio
async def test_the_node_refuses_a_services_object_with_no_guardrail():
    """The consumption side, and it was missing.

    The tests above pin that `OrchestrationServices` always *builds* a
    guardrail. That says nothing about the node, and a mutation restoring
    `getattr(self._services, "security_guardrail", None)` with the old
    privacy-only fallback reddened **none** of them -- so the control could have
    been re-weakened at the only place it is read, with every test still green.

    What has to hold: a services object without a guardrail is an error, not a
    quieter code path. Injection screening lives behind that attribute, and
    "this request was screened" must not depend on what a services object
    happens to carry.
    """

    from app.domain.errors import StageExecutionError
    from app.orchestration.langgraph.nodes import WorkflowNodeRuntime
    from app.orchestration.policies import ExecutionPolicy
    from app.orchestration.request import OrchestrationRequest, RequestActor
    from app.orchestration.timeout_control import ExecutionBudget, TimeoutConfig
    from app.pipeline.profiles import PipelineProfile
    from app.privacy.service import PrivacyService
    from app.services.security.access_scope import AccessScopeResolver

    class _GuardrailLess:
        """Everything privacy_permission used to need, and nothing more."""

        def __init__(self) -> None:
            self.privacy = PrivacyService()
            self.access_scope_resolver = AccessScopeResolver(document_provider=lambda actor: [])

        def report_event(self, event: object) -> None:
            del event

    runtime = WorkflowNodeRuntime(
        services=_GuardrailLess(),  # type: ignore[arg-type]
        policy=ExecutionPolicy.for_profile(PipelineProfile.ADVANCED),
        max_verifier_retries=1,
        context_token_budget=4000,
    )
    state = {
        "request": OrchestrationRequest(
            question="公司的年假有多少天",
            actor=RequestActor(user_id="u1", tenant_id="t1"),
        ),
        "budget": ExecutionBudget(TimeoutConfig()),
        "reporter": lambda event: None,
    }

    with pytest.raises(StageExecutionError):
        await runtime.privacy_permission(state)  # type: ignore[arg-type]
