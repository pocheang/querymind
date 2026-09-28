"""Pure policies that decide which optional orchestration stages are allowed."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.contracts import RouteDecision, TaskPlan
from app.pipeline.profiles import PipelineProfile


class UnsupportedRouteError(ValueError):
    """Raised when a router emits a route outside the profile contract."""


@dataclass(frozen=True)
class ExecutionPolicy:
    """One policy object selects profile behavior on the shared Engine."""

    profile: PipelineProfile = PipelineProfile.ADVANCED
    require_answer_validation: bool = False
    require_quality_report: bool = False
    allow_planning: bool = True
    # No "clarification": needing to ask a question is carried by
    # RouteDecision.clarification_fields, not by replacing the route, so a
    # clarifiable question keeps whatever retrieval the router chose for it.
    allowed_routes: frozenset[str] = frozenset({"vector", "graph", "web", "react", "hybrid"})

    @classmethod
    def for_profile(cls, profile: PipelineProfile | str) -> ExecutionPolicy:
        selected = PipelineProfile(profile)
        return cls(
            profile=selected,
            require_answer_validation=True,
            require_quality_report=True,
            allow_planning=True,
        )

    def validate_route(self, route: RouteDecision) -> None:
        actual = route.effective_route
        if actual not in self.allowed_routes:
            raise UnsupportedRouteError(f"unsupported route {actual!r} for {self.profile.value}")

    def should_plan(self, route: RouteDecision) -> bool:
        """Planner execution is allowed only when the router requires it."""
        return self.allow_planning and route.requires_plan

    def should_run_tools(self, route: RouteDecision, plan: TaskPlan | None) -> bool:
        """Run tools only for a tool-enabled route, and only as its plan allows.

        A route that asked for a plan still needs one that requires tools: when
        the planner times out the plan is None, and that has always meant tools
        stay off. A route that never asked for a plan -- a `vector` route whose
        specialist may consult its own read-only tools -- has no plan to wait
        for, and requiring one made those tools unreachable on every vector
        route: the planner is skipped, the plan stays None, the tools never run.
        """
        if "tool" not in route.allowed_capabilities:
            return False
        if route.requires_plan:
            return plan is not None and plan.requires_tools
        return True
