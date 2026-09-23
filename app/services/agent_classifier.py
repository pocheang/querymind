from app.services.query.keyword_match import any_keyword


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

    # The registry above is the one definition of the domain classes. This
    # function used to carry its own AI and security keyword lists as well --
    # copies of the registry's that had already drifted from it, and that could
    # only ever run when the registry had just answered "no match" to the same
    # words. What is left is the one class no registered specialist owns.
    #
    # Matched as words (`keyword_match`): `\bpdf\b` missed "这份pdf", because
    # to `\b` a CJK character is a word character.
    pdf_keywords = [
        "pdf",
        "pdf提取",
        "提取pdf",
        "读取pdf",
        "pdf文字",
        "pdf文本",
        "ocr",
        "图片",
        "图像",
        "照片",
        "截图",
        "image",
    ]
    if any_keyword(text, pdf_keywords):
        return "pdf_text"
    return "general"
