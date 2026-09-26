"""Which governed tools a request may be offered, given who is answering it.

Two ways into the tool stage, and they are not equally trusted:

- **Requested.** The router chose ``react`` (``intent="tool_call"``): the user
  asked for something to be done. Everything the actor may run stays on
  offer, narrowed to the answering specialist's category plus the general and
  system tools, and "no action taken" is reported, because the user is owed an
  answer about the action they asked for.
- **Consulted.** A specialist is answering an ordinary question and has tools
  of its own -- a CVE lookup, an ATT&CK lookup, a calculator. Only those are
  offered, and **only the ones that read**: a tool the user did not ask for may
  never change anything. When none fits, nothing is reported; telling the
  model "no action taken" on a question that asked for no action puts a
  sentence in the answer about something nobody wanted.

Until this module a specialist's tools were reachable only by the first way,
and the router reserves ``react`` for multi-step reasoning, so on a real model
none of six questions naming a CVE, a technique or a model size ever reached
them. ``default_tool_category`` existed on every specialist and nothing read it.

Nothing here reads evidence. It narrows the catalogue the selector sees; the
selector's inputs stay the user's own words (see ``selector.py``).
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.contracts import RouteDecision
from app.mcp.contracts import ToolDefinition
from app.tools.category import ToolCategory

#: Categories every specialist shares when the user asked for an action.
SHARED_TOOL_CATEGORIES: frozenset[str] = frozenset({ToolCategory.GENERAL, ToolCategory.SYSTEM})


def specialist_tool_category(agent_class: str) -> str | None:
    """The tool category of the specialist answering ``agent_class``, if any."""

    if not agent_class:
        return None
    from app.agents.registry import get_domain_agent_registry

    specialist = get_domain_agent_registry().get_agent(agent_class)
    category = getattr(specialist, "default_tool_category", None) if specialist is not None else None
    return str(category) if category else None


def specialist_offers_read_tools(agent_class: str) -> bool:
    """Whether the specialist for ``agent_class`` has any read-only tool at all.

    Asked of the tool providers rather than of an actor's catalogue: the router
    has no actor-specific view, and a catalogue the actor cannot use comes back
    empty at the tool stage and costs nothing there.
    """

    category = specialist_tool_category(agent_class)
    if category is None:
        return False
    from app.tools.registry import get_domain_tool_registry

    return any(tool.operation == "read" for tool in get_domain_tool_registry().get_tools_by_category(category))


def is_consulted(route: RouteDecision | None) -> bool:
    """True when the tool stage runs because a specialist, not the user, asked."""

    return route is not None and route.intent != "tool_call"


def catalog_for_route(catalog: Sequence[ToolDefinition], route: RouteDecision | None) -> tuple[ToolDefinition, ...]:
    """The part of ``catalog`` this request may be offered. See the module docstring."""

    everything = tuple(catalog)
    if route is None:
        return everything
    category = specialist_tool_category(route.agent_class)
    if is_consulted(route):
        if category is None:
            return ()
        return tuple(tool for tool in everything if tool.category == category and tool.operation == "read")
    if category is None:
        return everything
    allowed = SHARED_TOOL_CATEGORIES | {category}
    return tuple(tool for tool in everything if tool.category in allowed)


__all__ = [
    "SHARED_TOOL_CATEGORIES",
    "catalog_for_route",
    "is_consulted",
    "specialist_offers_read_tools",
    "specialist_tool_category",
]
