from app.services.language_detector import (
    detect_language,
    get_language_name,
    is_chinese_dominant,
)


def test_detect_pure_chinese():
    """Test detection of pure Chinese text"""
    result = detect_language("什么是零信任架构？")
    assert result == "zh"


def test_detect_pure_english():
    """Test detection of pure English text"""
    result = detect_language("What is zero trust architecture?")
    assert result == "en"


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
