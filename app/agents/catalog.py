"""Agent classes, in one place.

An agent class is what the router assigns a question to and what decides which
specialist answers it. Until this module the list of them was written out by
hand four times in the backend -- ``VALID_AGENT_CLASSES``, the API's
``_ALLOWED_AGENT_CLASSES``, the upload label guess and the LLM intent
classifier -- plus five copies of the ``AgentClassHint`` type in the frontend.
They had already disagreed: the intent classifier's copy lacked ``policy``, and
the two hint normalizers applied different rules, one consulting the specialist
registry and one not. A class missing from any one copy does not fail; it is
quietly treated as ``general``, which reads exactly like a question the router
simply did not recognise.

``StrEnum``, so members are strings and every comparison and serialization that
used a literal behaves the same. ``tests/agents/test_agent_class_vocabulary.py``
fails if a hand-written list of classes appears anywhere else, and checks the
frontend's list against this one.

Built-in classes are the ones the application ships. A specialist registered by
an extension adds its own class at runtime, which is why "is this a class?" is
answered by :func:`known_agent_classes` and not by the enum alone.
"""

from __future__ import annotations

import logging
from enum import StrEnum

from app.domain.text import normalize_string

logger = logging.getLogger(__name__)


class AgentClass(StrEnum):
    """Every agent class the application ships."""

    GENERAL = "general"
    CYBERSECURITY = "cybersecurity"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    PDF_TEXT = "pdf_text"
    # Assigned to uploads whose name reads like a policy document. No specialist
    # answers it yet, so a question routed here gets the general synthesizer.
    POLICY = "policy"


BUILTIN_AGENT_CLASSES: frozenset[str] = frozenset(AgentClass)
"""The shipped classes, as plain strings."""


def known_agent_classes() -> frozenset[str]:
    """The shipped classes plus every class a registered specialist declares.

    A registry that cannot be built is logged and leaves the built-ins in
    charge: routing must not fail because an extension did, but failing
    silently would make an unavailable specialist look like one never shipped.
    """

    try:
        from app.agents.registry import get_domain_agent_registry

        registered = get_domain_agent_registry().list_agent_classes()
    except Exception:  # an extension's agent module may raise anything
        logger.warning("domain agent registry unavailable; only built-in agent classes are known", exc_info=True)
        registered = ()
    return BUILTIN_AGENT_CLASSES | frozenset(registered)


def normalize_agent_class(value: str | None) -> str | None:
    """The canonical form of ``value`` if it names a known class, else None.

    Built-ins are checked first so the common case never builds the registry,
    which constructs every built-in specialist on first use.
    """

    name = normalize_string(value, lowercase=True)
    if not name:
        return None
    if name in BUILTIN_AGENT_CLASSES or name in known_agent_classes():
        return name
    return None


__all__ = [
    "BUILTIN_AGENT_CLASSES",
    "AgentClass",
    "known_agent_classes",
    "normalize_agent_class",
]
