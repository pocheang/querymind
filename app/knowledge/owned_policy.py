"""A compliance review's follow-up search, driven by the asker's own policy.

"我们的数据保留制度符合个保法吗？" names no topic. What points at the articles
that decide it -- retention periods, sensitive data, deletion -- is the text of
the policy under review, and the first search, run on the question alone,
measured returning the law's general provisions instead (A6, 2026-09-28).

This repository forbids retrieved content from steering retrieval, because the
author of a retrieved document is not always the person asking: a document that
argues for its own importance must not buy itself a wider search. This module is
the one exception, and it is bounded so that the reason for the rule does not
apply:

- Only a document the asker OWNS may supply queries -- by the registry's
  `owner_user_id`, never by a path or a chunk's own metadata. A shared, public
  or another user's document supplies nothing. So the text steering the search
  is text the asker put there, which is the same trust as the question itself.
- Only on a compliance gap analysis (`compliance` specialist, skill
  `compliance_gap_analysis`), where reviewing the asker's policy is the task.
- The follow-up search runs with the SAME access scope and keeps only documents
  labelled `compliance`. It can add regulation text the asker could already
  read; it can never reach anything the first search could not.
- Queries are the policy's own clauses, cut to a fixed length and count. No
  model reads them first, so there is nothing for an instruction in the text to
  address.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from app.agents.catalog import AgentClass
from app.domain.contracts import EvidenceItem

GAP_ANALYSIS_SKILL = "compliance_gap_analysis"

# How many of the policy's clauses become queries, and how long each may be.
# Bounded so a long policy cannot turn one question into a hundred searches.
MAX_POLICY_QUERIES = 4
MAX_QUERY_CHARS = 160
# A clause shorter than this is a heading or a fragment, not a practice.
_MIN_CLAUSE_CHARS = 12
# Paragraphs, and sentences within a long one.
_CLAUSE_BREAK = re.compile(r"\n[ \t]*\n|(?<=[。；;])")
_HEADING = re.compile(r"^#{1,6}[ \t]")

__all__ = [
    "GAP_ANALYSIS_SKILL",
    "MAX_POLICY_QUERIES",
    "is_owned_policy",
    "owned_policy_queries",
    "wants_owned_policy_followup",
]


def wants_owned_policy_followup(agent_class: str | None, skill: str | None) -> bool:
    """Only a compliance gap analysis reviews the asker's policy."""

    return agent_class == AgentClass.COMPLIANCE and (skill or "") == GAP_ANALYSIS_SKILL


def is_owned_policy(
    item: EvidenceItem,
    *,
    owner_user_id: str,
    owner_of: Callable[[str | None, str | None], str | None],
    label_of: Callable[[str | None, str | None], str | None],
) -> bool:
    """The asker's own document, and not itself regulation text."""

    if not owner_user_id:
        return False
    if owner_of(item.document_id, item.source) != owner_user_id:
        return False
    return label_of(item.document_id, item.source) != AgentClass.COMPLIANCE


def _clauses(text: str) -> Iterable[str]:
    for part in _CLAUSE_BREAK.split(text or ""):
        lines = [line.strip() for line in part.splitlines() if line.strip() and not _HEADING.match(line.strip())]
        clause = " ".join(lines)
        if len(clause) >= _MIN_CLAUSE_CHARS:
            yield clause[:MAX_QUERY_CHARS]


def owned_policy_queries(
    items: Iterable[EvidenceItem],
    *,
    owner_user_id: str,
    owner_of: Callable[[str | None, str | None], str | None],
    label_of: Callable[[str | None, str | None], str | None],
) -> tuple[str, ...]:
    """The first clauses of the asker's own policy documents, as search queries."""

    queries: list[str] = []
    for item in items:
        if not is_owned_policy(item, owner_user_id=owner_user_id, owner_of=owner_of, label_of=label_of):
            continue
        for clause in _clauses(item.content):
            if clause not in queries:
                queries.append(clause)
            if len(queries) >= MAX_POLICY_QUERIES:
                return tuple(queries)
    return tuple(queries)
