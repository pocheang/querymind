from app.agents.graph_rag_agent_enhanced import extract_document_entities


def test_extract_document_entities_filters_english_section_noise():
    text = """
    Introduction
    Overview
    Large Language Models (LLMs) are widely used in Natural Language Processing.
    Retrieval-Augmented Generation improves question answering quality.
    The Transformer architecture powers ChatGPT and GitHub Copilot.
    Description
    References
    """

    entities = extract_document_entities(text, limit=12)

    assert "Large Language Models" in entities
    assert "Natural Language Processing" in entities
    assert "Retrieval-Augmented Generation" in entities
    assert "LLMs" in entities
    assert "ChatGPT" in entities
    assert "Introduction" not in entities
    assert "Overview" not in entities
    assert "Description" not in entities
    assert "References" not in entities


def test_extract_document_entities_filters_chinese_sentence_fragments():
    text = """
    大语言模型（LLM）是一种基于深度学习的自然语言处理系统。主要特点包括：
    - 参数规模持续扩大
    - 支持检索增强生成
    - 应用于智能客服系统和机器翻译
    """

    entities = extract_document_entities(text, limit=12)

    assert "大语言模型" in entities
    assert "自然语言处理" in entities
    assert "检索增强生成" in entities
    assert "智能客服系统" in entities
    assert "机器翻译" in entities
    assert "主要特点包括" not in entities
    assert "是一种基于深度学习的自然语言处理系统" not in entities
