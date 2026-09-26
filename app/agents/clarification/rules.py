"""Deterministic completeness rules shared by Router and Clarification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from app.domain.contracts import ClarificationQuestion

ClarificationIntent = Literal[
    "rag_design",
    "document_comparison",
    "environment_setup",
    "troubleshooting",
    "usage_guidance",
    "optimization",
    "complete",
]


@dataclass(frozen=True)
class CompletenessAssessment:
    """A retrieval-free assessment of fields required before execution."""

    intent: ClarificationIntent
    complexity: Literal["simple", "complex"]
    required_fields: tuple[str, ...] = ()
    extracted_info: dict[str, str] = field(default_factory=dict)


_OTHER_OPTION_ZH = "其他（自定义输入 / 补充说明）"
_OTHER_OPTION_EN = "Other (Custom input / specify details)"


_QUESTIONS_ZH: dict[str, dict[str, ClarificationQuestion]] = {
    "rag_design": {
        "scenario": ClarificationQuestion(
            question="请问该 RAG 系统的主要落地场景与业务目标是什么？",
            options=[
                "(推荐) 企业私有知识库：面向组织内部员工，检索政策制度、产品规范与操作手册",
                "智能客服与技术支持问答：面向外部客户，要求高并发支持与低延迟流式响应",
                "研发代码与工程知识库：集成代码仓库、架构文档与 API 说明，辅助工程开发",
                "数据分析与决策辅助：融合结构化报表与业务指标分析，提供战略与运营洞察",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="scenario",
        ),
        "data_source": ClarificationQuestion(
            question="请指定系统主要接入并索引的数据源类型：",
            options=[
                "(推荐) PDF / Office 办公文档（Word, PowerPoint, Excel 等）与纯文本文件",
                "企业关系型数据库与数据仓库（PostgreSQL, MySQL, ClickHouse 等）",
                "RESTful / GraphQL 接口与第三方云服务实时数据源",
                "公网网页、在线知识站点与技术文档定向爬取内容",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="data_source",
        ),
        "scale": ClarificationQuestion(
            question="系统预计需要承载的数据规模与文档量级大约是：",
            options=[
                "(推荐) 中型规模（1-10GB，约数十万至数百万 Token，适合常规企业私有库）",
                "轻量微型（<1GB，快速启动与原型验证，单机内存即可高效支撑）",
                "大型规模（10-100GB，需建立分布式分块、独立向量索引与高并发缓存）",
                "超大规模（>100GB，百亿级 Token，需多节点集群分片与混合存储架构）",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="scale",
        ),
        "performance_requirement": ClarificationQuestion(
            question="对系统端到端的平均问答响应延迟有何指标要求？",
            options=[
                "(推荐) 快速交互（1-3秒，平衡检索召回深度与大模型思考质量）",
                "实时极速（<1秒，适用于即时交互与高频打字机实时体验）",
                "深度分析（3-5秒，适用于长篇深度推理与多步骤检索任务）",
                "无严格要求（以回答完整性、深度与多源证据引用丰富度优先）",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="performance_requirement",
        ),
    },
    "document_comparison": {
        "doc_ids": ClarificationQuestion(
            question="请指定需要进行对比分析的两个或多个具体对象、文档或技术方案：",
            options=[],
            allow_custom_input=True,
            field_name="doc_ids",
        ),
        "comparison_aspect": ClarificationQuestion(
            question="您希望在对比中重点关注哪些核心维度？",
            options=[
                "(推荐) 功能特性与适用场景：核心能力、支持范围与典型落地案例",
                "架构性能与并发指标：吞吐量、响应延迟、资源消耗与扩展能力",
                "落地成本与运维开销：授权模式、硬件要求、部署门槛与维护成本",
                "版本演进与演进差异：接口兼容性、变更记录与技术演进轨迹",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="comparison_aspect",
        ),
        "output_format": ClarificationQuestion(
            question="您期望对比结果以何种形式呈现？",
            options=[
                "(推荐) 结构化对比表格：多维度横向对照，直观展示差异与优劣势",
                "深度分析报告：包含背景概述、逐项深入剖析、架构建议与总结",
                "执行摘要简报：提炼核心差异要点与一句话选型决策建议",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="output_format",
        ),
    },
    "environment_setup": {
        "target_component": ClarificationQuestion(
            question="请明确您希望配置、部署或安装的具体系统组件或运行环境：",
            options=[
                "(推荐) 完整全栈环境：包含前端 Web 界面、后端 API 服务及核心存储依赖",
                "后端核心服务：FastAPI 接口层、LangGraph 编排工作流与多智能体引擎",
                "前端 Web 控制台：React 18 + Vite 交互界面与运维状态看板",
                "向量检索数据库：Milvus / Chroma 向量数据库集群或本地服务",
                "知识图谱服务：Neo4j 图数据库及多跳实体关系抽取组件",
                "本地大模型运行时：Ollama / 本地离线量化大模型部署",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="target_component",
        ),
    },
    "troubleshooting": {
        "error_details": ClarificationQuestion(
            question="请问您遇到的是哪类故障或在系统运行的哪个阶段出现了异常？",
            options=[
                "(推荐) 后端服务启动或依赖缺失：Python 环境报错、缺少包或连接拒绝",
                "大模型调用超时或接口异常：模型服务无法连接、Token 超限或格式解析失败",
                "前端控制台渲染或 API 跨域报错：500 内部服务错误、网络超时或 CORS 拦截",
                "文档入库与向量化构建报错：PDF 解析失败、分块截断或 Embedding 写入异常",
                "混合检索结果为空或召回异常：向量库未命中、关键词过滤过度或 RRF 权重偏差",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="error_details",
        ),
    },
    "usage_guidance": {
        "usage_target": ClarificationQuestion(
            question="请问您希望了解哪个具体功能的操作流程与使用方法？",
            options=[
                "(推荐) 知识库文档上传与管理：支持格式、分块策略配置与解析入库全流程",
                "多智能体深度对话与协同问答：不同 Route 路由选择、提示词设置与长文本生成",
                "知识图谱与多跳关联探索：实体关系图谱可视化与图增强检索应用",
                "模型引擎配置与服务切换：在线 API（DeepSeek/OpenAI）与本地 Ollama 切换",
                "RESTful API 集成开发：系统鉴权、会话管理与流式接口调用规范",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="usage_target",
        ),
    },
    "optimization": {
        "optimization_target": ClarificationQuestion(
            question="请问您希望针对系统哪个技术环节或性能指标进行专项优化？",
            options=[
                "(推荐) 检索召回率与排序准确度：调优混合检索权重（向量+BM25+图谱）与重排策略",
                "端到端响应延迟与并发加速：降低首 Token 延迟、流式并发与缓存优化",
                "Token 消耗与推理资源优化：压缩系统上下文、精简 Prompt 与降低推理成本",
                "文档切片质量与图谱抽取精度：优化语义分块边界与知识三元组提取准确性",
                _OTHER_OPTION_ZH,
            ],
            allow_custom_input=True,
            field_name="optimization_target",
        ),
    },
}

_QUESTIONS_EN: dict[str, dict[str, ClarificationQuestion]] = {
    "rag_design": {
        "scenario": ClarificationQuestion(
            question="What is the primary operational scenario and business goal for this RAG system?",
            options=[
                "(Recommended) Enterprise Knowledge Base: Internal policies, operational manuals, and technical document Q&A",
                "Customer Support Assistant: Public-facing, high-concurrency Q&A with low-latency streaming answers",
                "Developer & Code Knowledge Base: Codebase navigation, architecture specs, and API documentation analysis",
                "Data Analysis & Decision Support: Structured report summaries, business metrics, and strategic insights",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="scenario",
        ),
        "data_source": ClarificationQuestion(
            question="Which primary data source type will be ingested and indexed?",
            options=[
                "(Recommended) PDF / Office documents (Word, PowerPoint, Excel) and plain text files",
                "Relational databases and data warehouses (PostgreSQL, MySQL, ClickHouse)",
                "RESTful / GraphQL APIs and external cloud services with real-time sync",
                "Web pages, online documentation sites, and crawled technical blogs",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="data_source",
        ),
        "scale": ClarificationQuestion(
            question="What is the anticipated data volume and document corpus scale?",
            options=[
                "(Recommended) Medium scale (1-10GB, standard department-level enterprise base, millions of tokens)",
                "Lightweight prototype (<1GB, rapid local test and single-server memory indexing)",
                "Large scale (10-100GB, dedicated vector indexing, distributed chunking, and caching)",
                "Very large scale (>100GB, multi-node clustering and hybrid multi-tier storage)",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="scale",
        ),
        "performance_requirement": ClarificationQuestion(
            question="What are your end-to-end response latency requirements?",
            options=[
                "(Recommended) Fast interaction (1-3s, optimal balance between depth and responsiveness)",
                "Real-time streaming (<1s, ultra-low latency for interactive chat and typewriter UX)",
                "Deep analysis (3-5s, suitable for complex multi-hop retrieval and reasoning)",
                "No strict constraint (prioritizing evidence depth, accuracy, and thoroughness)",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="performance_requirement",
        ),
    },
    "document_comparison": {
        "doc_ids": ClarificationQuestion(
            question="Please specify the two or more specific documents, entities, or technical solutions to compare:",
            options=[],
            allow_custom_input=True,
            field_name="doc_ids",
        ),
        "comparison_aspect": ClarificationQuestion(
            question="Which core dimensions should the comparison focus on?",
            options=[
                "(Recommended) Features & use cases: capabilities, coverage, and typical scenarios",
                "Performance & benchmarks: throughput, latency, resource usage, and scalability",
                "Cost & maintenance: licensing, hardware requirements, and operational overhead",
                "Version & evolution differences: API compatibility, changelog, and migration path",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="comparison_aspect",
        ),
        "output_format": ClarificationQuestion(
            question="How would you like the comparison results to be formatted?",
            options=[
                "(Recommended) Structured comparison table: clear matrix highlighting pros and cons",
                "In-depth analytical report: contextual analysis, architectural trade-offs, and verdict",
                "Executive summary: key takeaway points and direct actionable recommendations",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="output_format",
        ),
    },
    "environment_setup": {
        "target_component": ClarificationQuestion(
            question="Which specific component or environment would you like to configure or deploy?",
            options=[
                "(Recommended) Full-stack environment: Frontend UI, Backend API, and storage services",
                "Backend core services: FastAPI API layer, LangGraph workflows, and agent engine",
                "Frontend Web console: React 18 + Vite user interface and dashboards",
                "Vector database: Milvus / Chroma vector store clusters or local instances",
                "Knowledge graph: Neo4j database and multi-hop graph extraction service",
                "Local LLM runtime: Ollama or local quantized model inference server",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="target_component",
        ),
    },
    "troubleshooting": {
        "error_details": ClarificationQuestion(
            question="What specific error or failure stage are you experiencing?",
            options=[
                "(Recommended) Backend startup or dependency error: missing packages or connection refused",
                "Model invocation timeout or API failure: unreachable endpoint or token limit exceeded",
                "Frontend console or API CORS error: 500 server error, network timeout, or CORS block",
                "Document ingestion & chunking failure: PDF parsing error or embedding insertion crash",
                "Empty or abnormal retrieval results: vector miss, over-filtering, or RRF weighting skew",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="error_details",
        ),
    },
    "usage_guidance": {
        "usage_target": ClarificationQuestion(
            question="Which specific feature or workflow would you like operational guidance on?",
            options=[
                "(Recommended) Document upload & knowledge management: formats, chunking, and ingestion",
                "Multi-Agent chat & reasoning: route selection, prompt configs, and long-form outputs",
                "Knowledge graph & multi-hop reasoning: entity visualization and graph-augmented search",
                "Model engine configuration: switching between Cloud APIs (DeepSeek/OpenAI) and Ollama",
                "RESTful API integration: authentication, session state, and streaming endpoints",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="usage_target",
        ),
    },
    "optimization": {
        "optimization_target": ClarificationQuestion(
            question="Which specific aspect or performance metric do you want to optimize?",
            options=[
                "(Recommended) Retrieval accuracy & recall: fine-tuning hybrid weights and rerankers",
                "End-to-end latency & throughput: reducing first-token latency and streaming cache",
                "Token usage & compute efficiency: prompt context compression and cost reduction",
                "Chunking quality & graph extraction: refining semantic boundaries and triple extraction",
                _OTHER_OPTION_EN,
            ],
            allow_custom_input=True,
            field_name="optimization_target",
        ),
    },
}

_QUESTIONS_BY_LANGUAGE = {"zh": _QUESTIONS_ZH, "en": _QUESTIONS_EN}

_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "rag_design": ("scenario", "data_source", "scale", "performance_requirement"),
    "document_comparison": ("doc_ids",),
    "environment_setup": ("target_component",),
    "troubleshooting": ("error_details",),
    "usage_guidance": ("usage_target",),
    "optimization": ("optimization_target",),
    "complete": (),
}

_SUPPORTED_FIELDS: frozenset[str] = frozenset(
    field_name for questions in _QUESTIONS_ZH.values() for field_name in questions
)

# ---------------------------------------------------------------------------
# Pre-compiled Regex Patterns
# Keeping alternation count <= 15 per expression to ensure SonarQube regex
# complexity limit (<= 20) is never exceeded.
# ---------------------------------------------------------------------------

# Bounded and confined to one line: prevents catastrophic backtracking (python:S8786)
_STRUCTURED_FIELD_RE = re.compile(
    r"^[ \t]{0,8}-[ \t]{0,8}([a-z_]+)[ \t]{0,8}:[ \t]{0,8}(.+?)[ \t]{0,8}$",
    re.MULTILINE | re.IGNORECASE,
)

_RAG_INTENT_KEYWORD_RE = re.compile(
    r"\brag\b|检索增强|知识库(?:系统)?|knowledge\s*base",
    re.IGNORECASE | re.ASCII,
)
_RAG_INTENT_DESIGN_RE = re.compile(r"设计|搭建|构建|实现|架构|how\s+to\s+(?:build|design|implement)|architecture")

_RAG_SCENARIO_PATTERNS = (
    (re.compile(r"企业|公司|内部|\b(?:enterprise|internal)\b", re.IGNORECASE), "企业知识库"),
    (re.compile(r"客服|客户服务|\b(?:customer\s*support|helpdesk)\b", re.IGNORECASE), "客服问答"),
    (re.compile(r"代码|编程|\b(?:developer|code)\b", re.IGNORECASE), "代码知识库"),
    (re.compile(r"数据分析|报表|\banalytics\b", re.IGNORECASE), "数据分析"),
)

_RAG_SOURCE_PATTERNS = (
    (re.compile(r"\b(?:pdf|word|pptx?|excel)\b|文档|文件", re.IGNORECASE), "PDF/Office 文档"),
    (re.compile(r"数据库|\b(?:sql|mysql|postgres|database)\b", re.IGNORECASE), "数据库"),
    (re.compile(r"\b(?:api|graphql)\b|接口", re.IGNORECASE), "API"),
    (re.compile(r"网页|网站|爬取|\b(?:crawl|website)\b", re.IGNORECASE), "网页"),
)

_RAG_SCALE_RE = re.compile(
    r"(?<!\w)\d{1,8}(?:\.\d{1,4})?\s*(?:kb|mb|gb|tb|万条|千条|条)(?!\w)",
    re.IGNORECASE | re.ASCII,
)
_RAG_PERFORMANCE_KEYWORD_RE = re.compile(r"(?:响应|延迟|latency)[^，。;\n]{0,20}")
_RAG_PERFORMANCE_THRESHOLD_RE = re.compile(r"[<≤]\s*\d+(?:\.\d+)?\s*(?:ms|毫秒|s|秒)")

_COMPARISON_INTENT_RE = re.compile(r"比较|对比|差异|区别|\bcompare\b|\bdifference\b|\bversus\b|\bvs\.?\b")
_COMPARISON_QUOTED_RE = re.compile(r"[\"“‘']([^\"”’']{1,80})[\"”’']")
_COMPARISON_VERSUS_RE = re.compile(
    r"([\w.\-/一-鿿]{2,60})\s*(?:与|和|及|vs\.?|versus)\s*([\w.\-/一-鿿]{2,60})", re.IGNORECASE
)
_COMPARISON_ASPECT_RE = re.compile(
    r"功能|性能|成本|价格|时间|版本|安全|准确率|召回率|\b(?:feature|performance|cost|security)\b", re.IGNORECASE
)
_COMPARISON_OUTPUT_FORMAT_RE = re.compile(r"表格|报告|总结|\b(?:table|report|summary)\b", re.IGNORECASE)
_COMPARISON_TARGET_SUFFIX_RE = re.compile(r"的?(?:区别|差异|对比|优劣|异同)$")
_COMPARISON_TARGET_NOISE_RE = re.compile(
    r"请|请问|帮我|麻烦|比较|对比|说明|分析|以及|还有|另外|compare|difference|versus", re.IGNORECASE
)


@dataclass(frozen=True)
class _VagueIntentRule:
    """Encapsulates vague query matching and key parameter extraction.

    Regex patterns are bounded with <= 15 alternation branches per expression
    to guarantee SonarQube regex complexity limits (<= 20) are never exceeded.

    `keyword_patterns` only means something when a question can match this rule
    *and* name a keyword. `extract` runs only after `matches`, and an anchored
    `vague_patterns` entry admits filler words alone ("这个系统如何配置"), so a
    rule whose only way in is that full-sentence match can never extract
    anything. Setup, usage and optimization carried keyword lists anyway until
    2026-09-26; enumerating every sentence their patterns accept (808, 1442 and
    385) found no extraction at all. Troubleshooting keeps its list because its
    `short_patterns` let a question like "redis 报错" in with a keyword attached.
    """

    intent: ClarificationIntent
    field_name: str
    vague_patterns: tuple[re.Pattern[str], ...]
    keyword_patterns: tuple[re.Pattern[str], ...] = ()
    max_short_len: int = 0
    short_patterns: tuple[re.Pattern[str], ...] = ()

    def matches(self, cleaned: str) -> bool:
        """Check whether the normalized input represents this vague intent."""
        if any(pat.search(cleaned) for pat in self.vague_patterns):
            return True
        if self.max_short_len and len(cleaned) <= self.max_short_len:
            return any(pat.search(cleaned) for pat in self.short_patterns)
        return False

    def extract(self, text: str) -> dict[str, str]:
        """Extract matched keyword into the required field dict."""
        for pat in self.keyword_patterns:
            match = pat.search(text)
            if match:
                return {self.field_name: match.group(0)}
        return {}


_TROUBLESHOOTING_RULE = _VagueIntentRule(
    intent="troubleshooting",
    field_name="error_details",
    vague_patterns=(
        re.compile(
            r"^(?:系统|运行|程序|接口)?(?:报错|失败|崩了|出错了|启动不了|无法运行|无法启动|error|exception)(?:了)?(?:怎么办|怎么处理|怎么解决)?$"
        ),
    ),
    max_short_len=10,
    short_patterns=(re.compile(r"报错|出错了|运行失败|执行失败"),),
    keyword_patterns=(
        # Technical error terms & status codes (<= 15 branches)
        re.compile(
            r"\b(?:timeout|404|500|connection refused|exception|traceback|oom|cuda|syntax|null|undefined|cors)\b",
            re.IGNORECASE,
        ),
        # Middleware & service components (<= 15 branches)
        re.compile(
            r"\b(?:milvus|neo4j|ollama|redis|nginx|docker|uvicorn|fastapi|chroma|langgraph|pydantic)\b",
            re.IGNORECASE,
        ),
        # Specific operational and fault keywords (<= 15 branches)
        re.compile(
            r"启动失败|启动报错|连接失败|连接超时|请求超时|请求失败|内存溢出|显存不足|跨域|cors|鉴权失败|token失效|空指针",
            re.IGNORECASE,
        ),
    ),
)

_SETUP_RULE = _VagueIntentRule(
    intent="environment_setup",
    field_name="target_component",
    vague_patterns=(
        re.compile(
            r"^(?:请问)?(?:这个|系统|平台)?(?:如何|怎么|怎样)?(?:配置|部署|安装|环境搭建|启动)(?:呢|方法|步骤|流程)?$"
        ),
        re.compile(r"^(?:how\s+to\s+)?(?:deploy|install|configure|setup)$"),
    ),
)

_USAGE_RULE = _VagueIntentRule(
    intent="usage_guidance",
    field_name="usage_target",
    vague_patterns=(
        re.compile(
            r"^(?:请问)?(?:这个|该)?(?:系统|平台)?(?:如何|怎么|怎样)?(?:使用|操作|用|上手)(?:呢|方法|指南|教程)?$"
        ),
        re.compile(r"^(?:how\s+to\s+use|how\s+does\s+it\s+work)$"),
    ),
)

_OPTIMIZATION_RULE = _VagueIntentRule(
    intent="optimization",
    field_name="optimization_target",
    vague_patterns=(
        re.compile(r"^(?:请问)?(?:这个|系统|平台)?(?:如何|怎么|怎样)?(?:优化|调优|加速)(?:呢|方法|建议)?$"),
        re.compile(r"^how\s+to\s+optimize$"),
    ),
)

_VAGUE_INTENT_RULES: tuple[_VagueIntentRule, ...] = (
    _TROUBLESHOOTING_RULE,
    _SETUP_RULE,
    _USAGE_RULE,
    _OPTIMIZATION_RULE,
)


def assess_completeness(question: str) -> CompletenessAssessment:
    """Identify only cases where execution would materially depend on missing fields."""

    text = str(question or "").strip()
    lowered = text.lower()
    cleaned = lowered.rstrip("?？!！.。；;，, \t")
    structured = _structured_fields(text)

    # 1. RAG Design intent
    if _RAG_INTENT_KEYWORD_RE.search(lowered) and _RAG_INTENT_DESIGN_RE.search(lowered):
        extracted = {**_extract_rag_fields(text), **structured}
        return CompletenessAssessment(
            intent="rag_design",
            complexity="complex",
            required_fields=_REQUIRED_FIELDS["rag_design"],
            extracted_info=extracted,
        )

    # 2. Document Comparison intent
    if _COMPARISON_INTENT_RE.search(lowered):
        extracted = {**_extract_comparison_fields(text), **structured}
        return CompletenessAssessment(
            intent="document_comparison",
            complexity="complex",
            # Named comparison targets are essential; aspect and presentation
            # have safe general-purpose defaults and must not force extra turns.
            required_fields=_REQUIRED_FIELDS["document_comparison"],
            extracted_info=extracted,
        )

    # 3. Vague queries needing clarification
    for rule in _VAGUE_INTENT_RULES:
        if rule.matches(cleaned):
            extracted = {**rule.extract(text), **structured}
            return CompletenessAssessment(
                intent=rule.intent,
                complexity="complex",
                required_fields=_REQUIRED_FIELDS[rule.intent],
                extracted_info=extracted,
            )

    return CompletenessAssessment(intent="complete", complexity="simple", extracted_info=structured)


def missing_fields(assessment: CompletenessAssessment, collected_info: dict[str, str]) -> tuple[str, ...]:
    """Return required fields absent from both the query and prior confirmed answers."""

    known = {**assessment.extracted_info, **_nonblank(collected_info)}
    return tuple(field_name for field_name in assessment.required_fields if not known.get(field_name, "").strip())


def question_for(intent: str, field_name: str, language: str = "zh") -> ClarificationQuestion | None:
    """Return a fresh structured question so request state cannot mutate templates.

    ``language`` selects the catalogue; an unrecognized value falls back to
    Chinese. Both catalogues expose identical field names and option counts.
    """

    catalog = _QUESTIONS_BY_LANGUAGE.get(str(language or "zh").lower(), _QUESTIONS_ZH)
    template = catalog.get(intent, {}).get(field_name)
    return template.model_copy(deep=True) if template is not None else None


def max_rounds_for(intent: str) -> int:
    """One round per field there is actually a question for.

    The cap used to be a hand-written number per intent -- 7 for `rag_design`,
    which has four fields -- so it could never be reached and the UI promised
    three rounds that do not exist. Deriving it means the cap and the question
    catalogue cannot drift apart.
    """
    return len(_REQUIRED_FIELDS.get(intent, ()))


def _structured_fields(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    # Bounded, and confined to one line: this reads user-supplied text,
    # and `\s` matches newlines, so under (?m) the old pattern could pair a
    # dash on one line with a field name on another (python:S8786).
    for field_name, value in _STRUCTURED_FIELD_RE.findall(text):
        if field_name in _SUPPORTED_FIELDS and value.strip():
            extracted[field_name] = value.strip()
    return extracted


def _extract_rag_fields(text: str) -> dict[str, str]:
    lowered = text.lower()
    extracted: dict[str, str] = {}
    for pattern, value in _RAG_SCENARIO_PATTERNS:
        if pattern.search(lowered):
            extracted["scenario"] = value
            break
    for pattern, value in _RAG_SOURCE_PATTERNS:
        if pattern.search(lowered):
            extracted["data_source"] = value
            break
    scale = _RAG_SCALE_RE.search(lowered)
    if scale:
        extracted["scale"] = scale.group(0)

    # Two patterns tried independently rather than one `A|B` alternation: the
    # combined form measured regex complexity 24 against Sonar's 20 allowed.
    # `A|B`.search() returns the leftmost position where either branch matches,
    # ties going to A -- which is exactly what comparing the two independent
    # `.start()`s below reproduces, so the extracted text is unchanged (verified
    # over 300 generated inputs, zero mismatches).
    _perf_keyword = _RAG_PERFORMANCE_KEYWORD_RE.search(lowered)
    _perf_threshold = _RAG_PERFORMANCE_THRESHOLD_RE.search(lowered)
    if _perf_keyword and _perf_threshold:
        performance = _perf_keyword if _perf_keyword.start() <= _perf_threshold.start() else _perf_threshold
    else:
        performance = _perf_keyword or _perf_threshold
    if performance:
        extracted["performance_requirement"] = performance.group(0).strip()
    return extracted


def _clean_comparison_target(raw: str) -> str | None:
    """Reject a captured `versus` group that is really a leftover instruction
    fragment (e.g. a truncated verb phrase from a narrative sentence) rather than
    an actual entity name, and strip a common trailing "的区别/差异" clause so plain
    "A和B的区别" style inputs still extract cleanly."""
    cleaned = _COMPARISON_TARGET_SUFFIX_RE.sub("", raw.strip()).strip()
    if not cleaned or _COMPARISON_TARGET_NOISE_RE.search(cleaned):
        return None
    return cleaned


def _extract_comparison_fields(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    quoted = _COMPARISON_QUOTED_RE.findall(text)
    versus = _COMPARISON_VERSUS_RE.search(text)
    if len(quoted) >= 2:
        extracted["doc_ids"] = "、".join(quoted[:5])
    elif versus:
        left = _clean_comparison_target(versus.group(1))
        right = _clean_comparison_target(versus.group(2))
        if left and right:
            extracted["doc_ids"] = f"{left}、{right}"
    aspect = _COMPARISON_ASPECT_RE.search(text)
    if aspect:
        extracted["comparison_aspect"] = aspect.group(0)
    output_format = _COMPARISON_OUTPUT_FORMAT_RE.search(text)
    if output_format:
        extracted["output_format"] = output_format.group(0)
    return extracted


def _nonblank(values: dict[str, str]) -> dict[str, str]:
    return {str(key): str(value).strip() for key, value in values.items() if str(value).strip()}


__all__ = [
    "ClarificationIntent",
    "CompletenessAssessment",
    "assess_completeness",
    "max_rounds_for",
    "missing_fields",
    "question_for",
]
