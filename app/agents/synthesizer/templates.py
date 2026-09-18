"""
Synthesis Agent Answer Templates by Query Type

Provides structured templates for different query types to enforce
citation discipline and reduce hallucinations.

Task 13: Citation-first generation templates
"""

from typing import Literal

__all__ = [
    "QUERY_TYPE_CONCEPT",
    "QUERY_TYPE_COMPARISON",
    "QUERY_TYPE_RELATIONSHIP",
    "QUERY_TYPE_PROCEDURAL",
    "QUERY_TYPE_GENERAL",
    "QueryType",
    "CONCEPT_TEMPLATE",
    "COMPARISON_TEMPLATE",
    "RELATIONSHIP_TEMPLATE",
    "PROCEDURAL_TEMPLATE",
    "GENERAL_TEMPLATE",
    "get_answer_template",
    "infer_query_type",
    "COT_REASONING_PROMPT",
    "COT_VISIBLE_REASONING_PROMPT",
    "get_cot_reasoning_prompt",
    "HEDGING_GUIDELINES",
    "get_hedging_guidelines",
]

# Query type constants
QUERY_TYPE_CONCEPT = "concept"
QUERY_TYPE_COMPARISON = "comparison"
QUERY_TYPE_RELATIONSHIP = "relationship"
QUERY_TYPE_PROCEDURAL = "procedural"
QUERY_TYPE_GENERAL = "general"

QueryType = Literal["concept", "comparison", "relationship", "procedural", "general"]


# ============================================================================
# Answer Templates by Query Type
# ============================================================================

CONCEPT_TEMPLATE = """
Answer template for comprehensive concept explanation (长文本详尽阐述):

1. Core definition and background context with citations [E1]
2. Architecture, key components, and working mechanisms (each mechanism detailed with citations)
3. Main characteristics, technical advantages, and practical application scenarios (cited)
4. Scope, operational boundaries, limitations, and trade-offs (cite sources or acknowledge gaps)

Citation rules:
- EVERY factual claim MUST have an evidence-marker citation, e.g. [E1]
- If information is not in context, explicitly state "根据提供的信息" (based on provided information)
- Use hedging language for uncertain or incomplete contexts: "部分应用包括..." (some applications include...)

Structure guidelines:
- Use clear Markdown headings (e.g., ### 1. 核心定义与背景, ### 2. 核心架构与原理解析, ### 3. 主要特征与应用场景, ### 4. 边界与注意事项)
- Elaborate in depth across multiple well-developed paragraphs; avoid one-line summaries.

Example structure:
### 1. 核心概念与背景定义
<concept> 是 <detailed definition and background> [E1]。它主要解决 <problem statement>，并在 <context> 中扮演关键角色 [E1]。

### 2. 核心工作机制与架构细节
该概念/技术的核心机制包括：
- <mechanism 1>：<detailed explanation of principles and data flow> [E1]
- <mechanism 2>：<detailed operational mechanism and technical points> [E2]

### 3. 主要特征与应用场景
- 主要优势：<advantage 1> [E1]，<advantage 2> [E2]
- 典型应用：<scenario 1> [E2]，以及 <scenario 2> [E3]

### 4. 边界范围与局限性
根据提供的信息，<limitations or boundary conditions> [E1]。
"""

COMPARISON_TEMPLATE = """
Answer template for comprehensive comparison questions (多维度长文本对比分析):

1. Comprehensive introduction of both subjects with contextual background and citations [E1][E2]
2. Multi-dimensional comparative analysis:
   - Structured comparison table summarizing key dimensions (features, architecture, performance, scenarios, limitations)
   - In-depth point-by-point narrative analysis expanding on each dimension in detail
3. Summary of key trade-offs, practical pros & cons, and selection guidelines with citations

Citation rules:
- Each comparison dimension MUST cite sources for BOTH subjects
- If one subject lacks context, explicitly state: "提供的信息中未包含<subject>的<aspect>" (provided information does not include...)
- Avoid subjective preference without citation

Structure guidelines:
- Organize with clear Markdown headings and structured tables followed by thorough explanatory paragraphs.
- Provide comprehensive long-text analysis detailing the technical nuances of each side.

Example structure:
### 1. 对比概述与背景
<A> 和 <B> 是在 <domain> 中的两种重要方案。<A> 主要侧重于 <focus A> [E1]，而 <B> 专注于 <focus B> [E2]。

### 2. 多维度详细对比分析
| 对比维度 | <A> | <B> | 证据支持 |
| :--- | :--- | :--- | :--- |
| 核心架构/方法 | <method A> | <method B> | [E1], [E2] |
| 性能与适用规模 | <perf A> | <perf B> | [E1], [E3] |
| 典型应用场景 | <scenario A> | <scenario B> | [E2], [E3] |

- **架构与实现差异**：<A> 采用 <architecture details> [E1]，其优势在于 <details>；相比之下，<B> 基于 <architecture details> [E2]，更适合 <details>。
- **场景与性能考量**：在 <scenario 1> 下，<A> 表现为 <details> [E1]；而在 <scenario 2> 下，<B> 则 <details> [E3]。

### 3. 选型建议与总结
根据提供的信息，如果需要 <requirement A>，建议优先选择 <A> [E1]；若场景偏向 <requirement B>，则 <B> 更为合适 [E2]。
"""

RELATIONSHIP_TEMPLATE = """
Answer template for relationship and interaction analysis (关系与因果机制长文本深析):

1. Establish background context for both entities/concepts with citations [E1][E2]
2. Direct relationship and structural connection mechanisms (detailed analysis with citations)
3. Step-by-step interaction workflow, cause-and-effect chain, and practical manifestations (cited)
4. Influence, dependencies, boundaries, and scope limitations

Citation rules:
- Direct relationship claim MUST have citation
- Supporting examples and causal links must cite sources
- If relationship is inferred, use hedging: "根据提供的信息，X和Y可能存在关联" (based on provided information, X and Y may be related)

Structure guidelines:
- Provide multi-paragraph in-depth narrative with Markdown headings and bulleted mechanistic breakdowns.

Example structure:
### 1. 实体背景与上下文定位
<X> 是 <definition X> [E1]；<Y> 则代表 <definition Y> [E2]。二者在 <system/domain> 协同构成关键环节。

### 2. 核心关系与交互机制
<X> 与 <Y> 的本质关系为 <relationship summary> [E1]。具体体现为：
- 数据与调用依赖：<how X feeds into or influences Y> [E1]
- 状态与反馈闭环：<interaction details and impact> [E2]

### 3. 具体表现形式与案例
在实际运行过程中，<X> 的变化直接影响 <Y> 的表现：例如 <concrete example and mechanism> [E1]。

### 4. 影响边界与分析总结
根据提供的信息，<X> 对 <Y> 的影响存在特定前提条件：<prerequisites and boundary constraints> [E2]。
"""

PROCEDURAL_TEMPLATE = """
Answer template for procedural/how-to questions (长文本流程与步骤操作详析):

1. Overview of the process, target outcome, and environment/prerequisites (each cited) [E1]
2. In-depth step-by-step breakdown:
   - Step objectives, operational commands/configurations, technical rationale, and detailed actions (cited)
3. Verification and validation methods (how to confirm success) [E2]
4. Important precautions, error handling, rollback, or edge cases (cited)

Citation rules:
- Each step MUST have supporting citation
- If steps are missing from context, explicitly state: "提供的信息中包含部分步骤" (provided information contains partial steps)
- Do not fabricate steps not in context

Structure guidelines:
- Use structured headings, numbered execution stages, and code blocks or parameter explanations.

Example structure:
### 1. 流程概述与前置准备
实现 <process> 的核心目标是 <goal> [E1]。
- 前置依赖：<prerequisites and environment> [E1]
- 适用范围：<scope> [E1]

### 2. 详细执行步骤
#### 步骤一：<step 1 name>
<detailed description of action 1> [E1]。需要注意的关键参数包括 <parameters> [E1]。

#### 步骤二：<step 2 name>
<detailed description of action 2> [E2]。该步骤的作用是 <rationale> [E2]。

#### 步骤三：<step 3 name>
<detailed description of action 3> [E3]。

### 3. 验证与结果确认
执行完成后，可通过 <verification method> 验证是否生效 [E2]。

### 4. 注意事项与异常处理
- 注意事项：<precaution> [E1]
- 边界说明：提供的材料涵盖以上步骤，若遇 <gap> 需参考对应扩展规范。
"""

GENERAL_TEMPLATE = """
Answer template for general questions (全面详尽长文本解答):

1. Comprehensive direct answer and contextual overview with citation [E1]
2. In-depth breakdown and systematic multi-dimensional analysis (each point fully detailed and cited)
3. Practical context, key factors, concrete examples, or technical details (cited)
4. Comprehensive summary and scope qualifications if needed (cited)

Citation rules:
- EVERY factual claim MUST have an evidence-marker citation, e.g. [E1]
- No citation = no claim (use hedging or acknowledge limitation)
- For broad questions with narrow context, scope the answer: "根据提供的信息，<scoped_answer>"

Structure guidelines:
- Use clear Markdown headings and structured paragraphs to elaborate in depth.

Example structure:
### 1. 核心解答与概述
关于 <question_restatement>：<core answer and overview> [E1]。从整体来看，这涉及到 <broader context> [E1]。

### 2. 深度剖析与关键要点
- **核心要点一**：<detailed elaboration and explanation> [E1]
- **核心要点二**：<detailed elaboration and technical mechanism> [E2]
- **影响要素与关键细节**：<in-depth analysis of factors> [E2]

### 3. 实际应用与扩展分析
在具体实践中，<application or extended scenario> [E1]。同时需要关注 <related considerations> [E3]。

### 4. 总结与说明边界
综上所述，<summary conclusion> [E1]。根据提供的信息，<boundary notes or limitations>。
"""


# ============================================================================
# Template Selection
# ============================================================================


def get_answer_template(query_type: QueryType) -> str:
    """
    Get answer template for specific query type.

    Args:
        query_type: Type of query (concept, comparison, relationship, procedural, general)

    Returns:
        Template string with citation guidelines
    """
    templates = {
        QUERY_TYPE_CONCEPT: CONCEPT_TEMPLATE,
        QUERY_TYPE_COMPARISON: COMPARISON_TEMPLATE,
        QUERY_TYPE_RELATIONSHIP: RELATIONSHIP_TEMPLATE,
        QUERY_TYPE_PROCEDURAL: PROCEDURAL_TEMPLATE,
        QUERY_TYPE_GENERAL: GENERAL_TEMPLATE,
    }
    return templates.get(query_type, GENERAL_TEMPLATE)


def infer_query_type(question: str) -> QueryType:
    """
    Infer query type from question text.

    Args:
        question: User question

    Returns:
        Inferred query type
    """
    question_lower = question.lower()

    # Comparison indicators
    comparison_keywords = [
        "比较",
        "对比",
        "区别",
        "差异",
        "vs",
        "versus",
        "compare",
        "difference between",
        "相比",
        "versus",
        "和...的区别",
    ]
    if any(kw in question_lower for kw in comparison_keywords):
        return QUERY_TYPE_COMPARISON

    # Relationship indicators
    relationship_keywords = [
        "关系",
        "关联",
        "联系",
        "影响",
        "作用",
        "relationship",
        "connection",
        "how does",
        "affect",
        "influence",
        "relate to",
        "与...的关系",
    ]
    if any(kw in question_lower for kw in relationship_keywords):
        return QUERY_TYPE_RELATIONSHIP

    # Procedural indicators
    procedural_keywords = [
        "如何",
        "怎么",
        "怎样",
        "步骤",
        "方法",
        "过程",
        "流程",
        "how to",
        "how do",
        "steps",
        "procedure",
        "process",
        "方式",
    ]
    if any(kw in question_lower for kw in procedural_keywords):
        return QUERY_TYPE_PROCEDURAL

    # Concept indicators (what is, define, explain)
    concept_keywords = [
        "什么是",
        "定义",
        "解释",
        "介绍",
        "含义",
        "what is",
        "what are",
        "define",
        "explain",
        "meaning of",
        "是什么",
    ]
    if any(kw in question_lower for kw in concept_keywords):
        return QUERY_TYPE_CONCEPT

    # Default to general
    return QUERY_TYPE_GENERAL


# ============================================================================
# Chain-of-Thought Reasoning Prompts
# ============================================================================

COT_REASONING_PROMPT = """
Before writing your reply, think through the following privately:

1. Query Analysis:
   - What is the user really asking?
   - What type of query is this (concept/comparison/relationship/procedural)?
   - What would be a complete answer?

2. Context Assessment:
   - What factual claims can I make from the provided context?
   - What citations support each claim?
   - What information is missing?

3. Citation Planning:
   - Which evidence marker ([E1], [E2], ...) supports each factual statement?
   - Are there unsupported claims I should remove or hedge?
   - Do I need to acknowledge information gaps?

4. Answer Structure:
   - How should I organize the answer (definition, comparison, steps, etc.)?
   - Where do citations fit naturally?
   - What hedging language is needed for uncertain areas?

None of this analysis belongs in your reply. Respond with only the final
answer, following the template for the query type with structured long-form
text and clear Markdown headings -- no headings repeating these thinking steps,
no restating these steps, and no mention of "chain of thought" or "analysis".
If you find yourself writing the steps above out anyway, put a line
containing only "Answer:" immediately before the real answer, so a reader
can tell the two apart.
"""

# The visible-reasoning sibling of `COT_REASONING_PROMPT` above: same four
# steps, opposite closing instruction. Selected only when the caller asked to
# see the reasoning (`use_reasoning=True` on the request, not the default) --
# `COT_REASONING_PROMPT` stays the default for everyone else, unchanged.
#
# The tag is the whole mechanism `extract_reasoning_block`
# (app/agents/synthesizer/citations.py) and the live stream splitter
# (app/agents/synthesizer/thinking_stream.py) rely on to find the boundary:
# both need a marker that cannot appear by accident, which is why the model is
# told to use it exactly once and never inside the answer itself.
COT_VISIBLE_REASONING_PROMPT = """
Before writing your reply, think through the following. Unlike a private
scratchpad, this reasoning IS meant to be shown to the reader -- write it out
in full between <think> and </think> tags, then write the final answer
immediately after the closing tag.

1. Query Analysis:
   - What is the user really asking?
   - What type of query is this (concept/comparison/relationship/procedural)?
   - What would be a complete answer?

2. Context Assessment:
   - What factual claims can I make from the provided context?
   - What citations support each claim?
   - What information is missing?

3. Citation Planning:
   - Which evidence marker ([E1], [E2], ...) supports each factual statement?
   - Are there unsupported claims I should remove or hedge?
   - Do I need to acknowledge information gaps?

4. Answer Structure:
   - How should I organize the answer (definition, comparison, steps, etc.)?
   - Where do citations fit naturally?
   - What hedging language is needed for uncertain areas?

Required shape, exactly:
<think>
(your reasoning through the four steps above, as prose)
</think>
(the final answer, following the template for the query type with structured
long-form text and clear Markdown headings -- no headings repeating the steps
above, no mention of "chain of thought", and no second <think> block)

The opening <think> must be the very first thing you write, and the tag must
appear nowhere else in your reply -- not around the answer, not inside it.
"""


def get_cot_reasoning_prompt(visible: bool = False) -> str:
    """
    Get chain-of-thought reasoning prompt for synthesis.

    Args:
        visible: Use the `<think>`-tagged variant that asks the model to show
            its reasoning, instead of the default variant that keeps it
            private. Only set when the caller opted in to seeing it.

    Returns:
        Chain-of-thought reasoning prompt
    """
    return COT_VISIBLE_REASONING_PROMPT if visible else COT_REASONING_PROMPT


# ============================================================================
# Hedging Language Guidelines
# ============================================================================

HEDGING_GUIDELINES = """
Hedging Language Guidelines (for uncertain or incomplete contexts):

Chinese hedging phrases:
- "根据提供的信息" (based on provided information)
- "部分<noun>包括" (some <noun> include)
- "可能" (may/might) - use sparingly and with context
- "一般来说" (generally speaking)
- "在某些情况下" (in some cases)
- "提供的信息中提到" (the provided information mentions)
- "有限的信息显示" (limited information shows)

English hedging phrases:
- "based on the provided information"
- "some examples include"
- "may" or "might" - use sparingly and with context
- "generally"
- "in some cases"
- "according to the available context"
- "limited information suggests"

When to hedge:
- Broad questions with narrow context (e.g., "all applications" when context lists 2)
- Inferences not directly stated in context
- Partial information about a topic
- When connecting information across documents without explicit link

When NOT to hedge:
- Direct facts from context with clear citations
- Well-supported claims with multiple citations
- Don't over-hedge to the point of being unhelpful
"""


def get_hedging_guidelines() -> str:
    """
    Get hedging language guidelines.

    Returns:
        Hedging guidelines string
    """
    return HEDGING_GUIDELINES
