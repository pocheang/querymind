"""Measure which specialist answers each question in config/eval/specialist_routing.json.

    python scripts/eval_specialist_routing.py          # the offline keyword rules
    python scripts/eval_specialist_routing.py --llm    # the model router, as configured

The rules are what answers when the model router times out or is unavailable,
and they are pinned question by question in tests/evaluation. This command
prints the same measurement for a person, and exits 1 when the rules disagree
with the recorded state (a new miss, or a recorded miss that now routes right).

`--llm` measures the router the chat path actually uses. It is a manual command
for the reason `eval_full_pipeline.py` is: it needs a real chat model, and it
refuses (exit 2) rather than report a number about the offline stand-in, which
routes by keyword and would describe the rules a second time.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass

REFUSED = 2


def _print_summary(report) -> None:
    print(f"questions      : {len(report.outcomes)}")
    print(f"class accuracy : {report.class_accuracy:.4f}")
    print(f"skill accuracy : {report.skill_accuracy:.4f}  (scored where the class was right)")
    print("per class      :")
    for agent_class, (correct, total) in sorted(report.per_class.items()):
        print(f"  {agent_class:<24} {correct}/{total}")


def _print_misses(report, known: dict | None) -> int:
    """Every miss, marked against the record when there is one. Returns how many are not on it."""

    unrecorded = 0
    print("misses         :")
    for case_id, got in report.observed_misroutes().items():
        case = next(outcome.case for outcome in report.outcomes if outcome.case.id == case_id)
        marker = ""
        if known is not None:
            recorded = known.get(case_id, (None, ""))[0]
            marker = "known" if recorded == got else "NEW  "
            unrecorded += recorded != got
        print(f"  {marker} {case_id:<8} want {case.agent_class}/{case.skill}  got {got[0]}/{got[1]}  | {case.question}")
    return unrecorded


def _print_report(report, *, known: dict | None) -> int:
    """Print the measurement; return how far it drifted from `known` (0 when there is no record)."""

    _print_summary(report)
    drift = _print_misses(report, known)
    if known is not None:
        fixed = [case_id for case_id in known if case_id not in report.observed_misroutes()]
        for case_id in fixed:
            print(f"  FIXED {case_id}: routes as labelled now -- delete its KNOWN_MISROUTES entry")
        drift += len(fixed)
    return drift


def _chat_model_refusal() -> str | None:
    from app.services.models.effective import effective_model_configuration

    for component in effective_model_configuration():
        if component.component == "chat" and component.status != "active":
            return f"chat model is {component.status} ({component.configured}); the model router cannot be measured"
    return None


def _llm_route(question: str) -> tuple[str, str]:
    from app.agents.router.service import RouterAgentService
    from app.orchestration.request import OrchestrationRequest, RequestActor, RequestScope

    request = OrchestrationRequest(
        question=question,
        actor=RequestActor(user_id="routing-eval", tenant_id="routing-eval", role="viewer"),
        source_scope=RequestScope(),
    )
    route = asyncio.run(RouterAgentService().route(request))
    return route.agent_class, route.skill


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--llm", action="store_true", help="measure the model router instead of the offline rules")
    args = parser.parse_args(argv)

    from app.evaluation.specialist_routing import KNOWN_MISROUTES, evaluate, load_cases

    cases = load_cases()
    if not args.llm:
        drift = _print_report(evaluate(cases), known=KNOWN_MISROUTES)
        return 1 if drift else 0

    refusal = _chat_model_refusal()
    if refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return REFUSED
    started = time.perf_counter()
    report = evaluate(cases, route=_llm_route)
    print(f"model router, {time.perf_counter() - started:.0f}s")
    _print_report(report, known=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
