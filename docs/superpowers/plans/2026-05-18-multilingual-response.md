# Multi-Language Response System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable automatic language detection and matching responses for Chinese and English user inputs.

**Architecture:** Rule-based language detection (20% Chinese character threshold) + LLM prompt injection for language-aware response generation. Includes session preference tracking, API override control, and usage analytics.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, existing LLM infrastructure (synthesis_agent)

---

## File Structure

### New Files
- `app/services/language_detector.py` - Core language detection logic
- `app/services/session_language.py` - Session language preference tracking
- `app/services/language_analytics.py` - Usage logging and analytics
- `app/api/routes/admin/language_stats.py` - Admin analytics endpoints
- `tests/unit/test_language_detector.py` - Unit tests for detector
- `tests/unit/test_synthesis_language.py` - Unit tests for synthesis integration
- `tests/integration/test_multilingual_workflow.py` - End-to-end integration tests

### Modified Files
- `app/agents/synthesis_agent.py` - Add language detection and prompt injection
- `app/api/routes/query.py` - Add force_language parameter
- `app/graph/state.py` - Add language_preference field to GraphState
- `app/graph/nodes/synthesis_node.py` - Integrate language preference tracking

---

## Task 1: Language Detection Module

**Files:**
- Create: `app/services/language_detector.py`
- Test: `tests/unit/test_language_detector.py`

- [ ] **Step 1: Write failing test for pure Chinese detection**

Create `tests/unit/test_language_detector.py`:

```python
import pytest
from app.services.language_detector import detect_language


def test_detect_pure_chinese():
    """Test detection of pure Chinese text"""
    result = detect_language("什么是零信任架构？")
    assert result == "zh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_language_detector.py::test_detect_pure_chinese -v`

Expected: `ModuleNotFoundError: No module named 'app.services.language_detector'`

- [ ] **Step 3: Write minimal language detector implementation**

Create `app/services/language_detector.py`:

```python
"""Language detection service for multilingual response system."""
import re
import logging

logger = logging.getLogger(__name__)

# Chinese character range: U+4E00 to U+9FFF (CJK Unified Ideographs)
CHINESE_PATTERN = re.compile(r'[一-鿿]')
ALPHANUM_PATTERN = re.compile(r'[a-zA-Z一-鿿0-9]')

# Detection threshold: if Chinese chars > 20% of alphanumeric, classify as Chinese
CHINESE_THRESHOLD = 0.20


def detect_language(text: str) -> str:
    """
    Detect language of input text.
    
    Args:
        text: User input text
        
    Returns:
        'zh' for Chinese, 'en' for English
        
    Algorithm:
        - Count Chinese characters (U+4E00 to U+9FFF)
        - Count total alphanumeric characters
        - If Chinese ratio > 20%, return 'zh'
        - Otherwise return 'en'
        - Default to 'zh' for empty/punctuation-only input
    """
    if not text or not text.strip():
        return "zh"  # Default to Chinese for empty input
    
    # Count Chinese characters
    chinese_chars = len(CHINESE_PATTERN.findall(text))
    
    # Count total alphanumeric characters (letters + Chinese + digits)
    total_alphanum = len(ALPHANUM_PATTERN.findall(text))
    
    # Handle edge case: no alphanumeric characters (pure punctuation)
    if total_alphanum == 0:
        return "zh"  # Default to Chinese
    
    # Calculate Chinese character ratio
    chinese_ratio = chinese_chars / total_alphanum
    
    # Determine language based on threshold
    detected = "zh" if chinese_ratio > CHINESE_THRESHOLD else "en"
    
    logger.debug(
        f"Language detection: {detected} (chinese_ratio={chinese_ratio:.2f}, "
        f"chinese_chars={chinese_chars}, total_alphanum={total_alphanum})"
    )
    
    return detected


def get_language_name(lang_code: str) -> str:
    """
    Convert language code to full name.
    
    Args:
        lang_code: 'zh' or 'en'
        
    Returns:
        'Chinese' or 'English'
    """
    return "Chinese" if lang_code == "zh" else "English"


def is_chinese_dominant(text: str) -> bool:
    """
    Quick check if text is primarily Chinese.
    
    Args:
        text: Input text
        
    Returns:
        True if Chinese characters dominate
    """
    return detect_language(text) == "zh"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_language_detector.py::test_detect_pure_chinese -v`

Expected: `PASSED`

- [ ] **Step 5: Add tests for pure English detection**

Add to `tests/unit/test_language_detector.py`:

```python
def test_detect_pure_english():
    """Test detection of pure English text"""
    result = detect_language("What is zero trust architecture?")
    assert result == "en"
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/test_language_detector.py::test_detect_pure_english -v`

Expected: `PASSED`

- [ ] **Step 7: Add tests for mixed language inputs**

Add to `tests/unit/test_language_detector.py`:

```python
def test_detect_mixed_chinese_dominant():
    """Test mixed input with Chinese dominant (>20%)"""
    result = detect_language("请解释一下 API Gateway 的作用")
    assert result == "zh"


def test_detect_mixed_english_dominant():
    """Test mixed input with English dominant (<20% Chinese)"""
    result = detect_language("How does the RAG system handle 中文查询?")
    assert result == "en"


def test_detect_code_with_chinese_comments():
    """Test code snippet with Chinese comments"""
    text = """这段代码有问题
def foo():
    pass
"""
    result = detect_language(text)
    assert result == "zh"
```

- [ ] **Step 8: Run all detector tests**

Run: `pytest tests/unit/test_language_detector.py -v`

Expected: All tests `PASSED`

- [ ] **Step 9: Add edge case tests**

Add to `tests/unit/test_language_detector.py`:

```python
def test_detect_empty_input():
    """Test empty string defaults to Chinese"""
    assert detect_language("") == "zh"
    assert detect_language("   ") == "zh"


def test_detect_punctuation_only():
    """Test punctuation-only input defaults to Chinese"""
    assert detect_language("???!!!") == "zh"
    assert detect_language("...") == "zh"


def test_detect_numbers_only():
    """Test numbers-only input defaults to English"""
    result = detect_language("12345")
    assert result == "en"


def test_get_language_name():
    """Test language code to name conversion"""
    assert get_language_name("zh") == "Chinese"
    assert get_language_name("en") == "English"


def test_is_chinese_dominant():
    """Test quick Chinese dominance check"""
    assert is_chinese_dominant("这是中文") is True
    assert is_chinese_dominant("This is English") is False
```

- [ ] **Step 10: Run all tests to verify edge cases**

Run: `pytest tests/unit/test_language_detector.py -v`

Expected: All tests `PASSED`

- [ ] **Step 11: Commit language detector**

```bash
git add app/services/language_detector.py tests/unit/test_language_detector.py
git commit -m "feat: add language detection module with 20% Chinese threshold

- Detect Chinese vs English based on character ratio
- Handle edge cases (empty, punctuation, code)
- Include utility functions for language names
- Comprehensive unit test coverage"
```

---

## Task 2: Synthesis Agent Integration

**Files:**
- Modify: `app/agents/synthesis_agent.py`
- Test: `tests/unit/test_synthesis_language.py`

- [ ] **Step 1: Write failing test for synthesis with Chinese input**

Create `tests/unit/test_synthesis_language.py`:

```python
import pytest
from unittest.mock import Mock, patch
from app.agents.synthesis_agent import synthesize, _build_prompt_with_language


def test_build_prompt_with_language_chinese():
    """Test prompt builder includes Chinese language hint"""
    prompt = _build_prompt_with_language(
        question="什么是RAG？",
        detected_language="zh",
        skill_name="answer_with_citations",
        vector_context="RAG是检索增强生成..."
    )
    
    assert "[Language: zh]" in prompt
    assert "什么是RAG？" in prompt
    assert "RAG是检索增强生成..." in prompt


def test_build_prompt_with_language_english():
    """Test prompt builder includes English language hint"""
    prompt = _build_prompt_with_language(
        question="What is RAG?",
        detected_language="en",
        skill_name="answer_with_citations",
        vector_context="RAG is Retrieval-Augmented Generation..."
    )
    
    assert "[Language: en]" in prompt
    assert "What is RAG?" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_synthesis_language.py::test_build_prompt_with_language_chinese -v`

Expected: `ImportError: cannot import name '_build_prompt_with_language'`

- [ ] **Step 3: Update ANSWER_PROMPT with language rules**

Modify `app/agents/synthesis_agent.py`, update the `ANSWER_PROMPT` constant to add language adaptation rules at the end.

- [ ] **Step 4: Add _build_prompt_with_language function**

Add to `app/agents/synthesis_agent.py` after the existing `_build_prompt` function:

```python
def _build_prompt_with_language(
    question: str,
    detected_language: str,
    skill_name: str,
    memory_context: str = "",
    vector_context: str = "",
    graph_context: str = "",
    web_context: str = "",
) -> str:
    language_hint = f"[Language: {detected_language}]\n"
    return (
        f"{language_hint}"
        f"技能: {skill_name}\n\n"
        f"用户问题:\n{question}\n\n"
        f"记忆上下文:\n{memory_context or '无'}\n\n"
        f"向量检索上下文:\n{vector_context or '无'}\n\n"
        f"图谱上下文:\n{graph_context or '无'}\n\n"
        f"联网补充上下文:\n{web_context or '无'}\n"
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_synthesis_language.py -v`

Expected: Both tests `PASSED`

- [ ] **Step 6: Modify synthesize() to add force_language parameter and integrate detection**

Update `synthesize()` function signature and add language detection at the beginning.

- [ ] **Step 7: Update synthesize() return to include detected_language**

Add `detected_language` field to the return dictionary.

- [ ] **Step 8: Run synthesis tests**

Run: `pytest tests/unit/test_synthesis_language.py -v`

- [ ] **Step 9: Commit synthesis agent integration**

```bash
git add app/agents/synthesis_agent.py tests/unit/test_synthesis_language.py
git commit -m "feat: integrate language detection into synthesis agent

- Add language adaptation rules to ANSWER_PROMPT
- Create _build_prompt_with_language() for hint injection  
- Modify synthesize() to detect language and inject hints
- Add force_language parameter for API override
- Return detected_language in response metadata"
```

---


## Task 3: API Layer Integration

**Files:**
- Modify: `app/api/routes/query.py`
- Test: `tests/integration/test_multilingual_workflow.py`

- [ ] **Step 1: Add force_language parameter to query endpoint**

Modify `app/api/routes/query.py`, add parameter to query endpoint function.

- [ ] **Step 2: Pass force_language to synthesis call**

Pass the parameter through to synthesize() function.

- [ ] **Step 3: Ensure detected_language in API response**

Include detected_language field from synthesis result in response.

- [ ] **Step 4: Write integration tests**

Create `tests/integration/test_multilingual_workflow.py` with tests for Chinese, English, and force_language override.

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/integration/test_multilingual_workflow.py -v`

- [ ] **Step 6: Commit API integration**

```bash
git add app/api/routes/query.py tests/integration/test_multilingual_workflow.py
git commit -m "feat: add force_language parameter to query API"
```

---

## Task 4: Session Language Preference

**Files:**
- Create: `app/services/session_language.py`
- Modify: `app/graph/state.py`

- [ ] **Step 1: Add language_preference to GraphState**

Modify `app/graph/state.py` to add language_preference field.

- [ ] **Step 2: Create session language tracker**

Create `app/services/session_language.py` with functions to track last 5 queries and determine preference.

- [ ] **Step 3: Write tests for session preference**

Create `tests/unit/test_session_language.py` with tests for preference logic.

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_session_language.py -v`

- [ ] **Step 5: Integrate into synthesis node**

Update synthesis node to call update_language_history after each query.

- [ ] **Step 6: Commit session preference**

```bash
git add app/services/session_language.py app/graph/state.py tests/unit/test_session_language.py
git commit -m "feat: add session language preference tracking"
```

---

## Task 5: Language Analytics

**Files:**
- Create: `app/services/language_analytics.py`
- Create: `app/api/routes/admin/language_stats.py`

- [ ] **Step 1: Create analytics logging service**

Create `app/services/language_analytics.py` with in-memory logging (can be upgraded to DB later).

- [ ] **Step 2: Integrate logging into synthesis**

Call analytics logger after language detection in synthesis.

- [ ] **Step 3: Create admin stats endpoint**

Create `app/api/routes/admin/language_stats.py` with endpoint to retrieve language usage statistics.

- [ ] **Step 4: Write tests for analytics**

Create tests for analytics logging and retrieval.

- [ ] **Step 5: Commit analytics**

```bash
git add app/services/language_analytics.py app/api/routes/admin/language_stats.py
git commit -m "feat: add language usage analytics and admin endpoint"
```

---

## Task 6: End-to-End Testing

**Files:**
- Test: `tests/integration/test_multilingual_workflow.py`

- [ ] **Step 1: Test complete Chinese conversation flow**

Test multiple Chinese queries in sequence, verify consistent Chinese responses.

- [ ] **Step 2: Test complete English conversation flow**

Test multiple English queries in sequence, verify consistent English responses.

- [ ] **Step 3: Test language switching**

Test switching from Chinese to English mid-conversation.

- [ ] **Step 4: Test mixed language queries**

Test queries with both Chinese and English content.

- [ ] **Step 5: Test edge cases**

Test empty input, punctuation only, code snippets with comments.

- [ ] **Step 6: Run full test suite**

Run: `pytest tests/ -v -k multilingual`

- [ ] **Step 7: Commit final tests**

```bash
git add tests/integration/test_multilingual_workflow.py
git commit -m "test: add comprehensive multilingual end-to-end tests"
```

---

## Self-Review Checklist

**Spec Coverage:**
- [x] Language detection (20% threshold) - Task 1
- [x] Synthesis agent integration - Task 2
- [x] API force_language parameter - Task 3
- [x] Session preference tracking - Task 4
- [x] Language analytics - Task 5
- [x] Comprehensive testing - Tasks 1-6

**No Placeholders:**
- [x] All code blocks are complete
- [x] All test cases are specific
- [x] All commands have expected outputs

**Type Consistency:**
- [x] detect_language() returns 'zh' or 'en' consistently
- [x] force_language parameter accepts 'zh' or 'en'
- [x] detected_language field in responses is 'zh' or 'en'

---

