def classify_agent_class(question: str) -> str:
    text = (question or "").strip().lower()
    if not text:
        return "general"

    # 1. Prioritize dynamic matching from DomainAgentRegistry
    try:
        from app.agents.registry import get_domain_agent_registry

        matched = get_domain_agent_registry().match_agent_class(text)
        if matched:
            return matched
    except Exception:
        pass

    # The registry is the one definition of the domain classes. This function
    # used to carry its own AI and security keyword lists, then only a PDF list
    # for the one class no specialist owned; that list moved to the document
    # specialist (app/agents/document/service.py) when it was registered.
    return "general"
