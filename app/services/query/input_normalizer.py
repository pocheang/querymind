import logging
import re
import unicodedata

from app.core.config import get_settings
from app.services.security.injection_defense import TextDeobfuscator, detect_prompt_injection

logger = logging.getLogger(__name__)

_MULTI_PUNCT_RE = re.compile(r"[!?！？。．\.]{3,}")
_SPACE_RE = re.compile(r"[ \u3000\t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_MULTI_REPEAT_CHAR_RE = re.compile(r"(.)\1{5,}")

_PROMPT_INJECTION_RE = re.compile(
    r"(ignore\s+(all\s+)?previous\s+instructions|"
    r"reveal\s+system\s+prompt|"
    r"you\s+are\s+now\s+developer|"
    r"忽略(之前|以上|所有)?(系统|开发者)?指令|"
    r"输出(系统|开发者)提示词|"
    r"越狱提示词|"
    r"绕过安全策略)",
    flags=re.IGNORECASE,
)
_INCOMPLETE_REFER_RE = re.compile(
    r"(这个|那个|上面|前面|如下|这里|它|他|她|该项|这个问题|那个问题)",
    flags=re.IGNORECASE,
)
_SHORT_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9_]+")


def normalize_user_question(question: str) -> str:
    cleaned = TextDeobfuscator.clean(str(question or ""))
    text = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    chars: list[str] = []
    for ch in text:
        if ch in ("\n", "\t"):
            chars.append(ch)
            continue
        if unicodedata.category(ch).startswith("C"):
            continue
        chars.append(ch)
    text = "".join(chars)

    lines = [_SPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    text = _MULTI_REPEAT_CHAR_RE.sub(lambda m: m.group(1) * 3, text)
    text = _MULTI_PUNCT_RE.sub(lambda m: m.group(0)[:2], text).strip()

    if not text:
        raise ValueError("question is empty after normalization")
    return text


class QuestionBlockedError(ValueError):
    """A question the input screening refuses. The API answers 422, not 500.

    A subclass of ValueError so existing callers that catch ValueError keep
    working; the query endpoint catches this one first, because a refusal is a
    fact about the question and a 500 sends an operator to look at the service.
    """


def validate_user_question_security(question: str) -> None:
    """Refuse instructions aimed at the assistant, judged by intent.

    A keyword rule used to run first: a dangerous command anywhere in the
    question plus any word from an "action" list (执行, run, bash, shell...)
    blocked it. "vssadmin delete shadows 被执行了怎么办？" -- an incident-response
    question for the security specialist -- matched both, because 被执行了
    ("was executed") contains 执行. `detect_prompt_injection` already blocks a
    dangerous command only when it is a request to run it ("帮我执行 rm -rf"),
    so the keyword rule added nothing but refusals of defensive questions.
    """
    text = str(question or "")
    settings = get_settings()
    defense_enabled = bool(getattr(settings, "prompt_injection_defense_enabled", True))
    if defense_enabled:
        assessment = detect_prompt_injection(text)
        if assessment.is_blocked:
            logger.warning(
                "Prompt injection blocked: threat=%s risk=%.2f rules=%s",
                assessment.threat_type,
                assessment.risk_score,
                assessment.matched_rules,
            )
            raise QuestionBlockedError(
                f"question blocked: prompt-injection like instruction detected ({assessment.threat_type.value if assessment.threat_type else 'threat'})"
            )
    else:
        # Fallback legacy regex if defense is explicitly disabled
        injection = _PROMPT_INJECTION_RE.search(text)
        if injection:
            raise QuestionBlockedError("question blocked: prompt-injection like instruction detected")


def normalize_and_validate_user_question(question: str) -> str:
    normalized = normalize_user_question(question)
    validate_user_question_security(normalized)
    return normalized


def enhance_user_question_for_completion(question: str) -> str:
    """
    Improve short/underspecified user questions so downstream agents can
    reason with clearer constraints while preserving the original intent text.
    """
    text = normalize_user_question(question)
    tokens = _SHORT_TOKEN_RE.findall(text)
    too_short = len(text) <= 12 or (len(text) <= 24 and len(tokens) <= 3)
    has_refer = bool(_INCOMPLETE_REFER_RE.search(text))
    likely_incomplete = too_short or has_refer
    if not likely_incomplete:
        return text

    return (
        f"{text}\n\n"
        "[补全提示]\n"
        "- 优先按用户当前这条最新提问作答，不要被更早轮次覆盖。\n"
        "- 用户提问可能信息不完整，请先结合当前会话上下文补全语义。\n"
        "- 若仍缺少关键条件，请先列出缺失信息，再在明确假设下给出可执行建议。\n"
        "- 回答需包含：结论、执行步骤、风险点。"
    )
