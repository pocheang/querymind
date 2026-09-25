import logging
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource

logger = logging.getLogger(__name__)


DEFAULT_ENVIRONMENT = "development"

# The short forms in circulation, and what each one means. `deploy/scripts/config.py`
# renders exactly `development`, `test` and `production`, so these are the names a
# `.runtime/*.env` file can actually have.
_ENVIRONMENT_ALIASES = {"dev": "development", "prod": "production"}


def normalise_environment_name(raw: object) -> str:
    """One answer to "what environment is this", for every reader of APP_ENV.

    There were three spellings and no agreement between them. `Settings.app_env`
    defaulted to `"dev"` while `resolve_runtime_env_file` defaulted to
    `"development"`; that function mapped `dev` to `development` and knew nothing
    about `prod`; and two consumers tested membership of `{"prod", "production"}`
    while the render step only accepts the long forms.

    `APP_ENV=prod` was the expensive combination. `resolve_runtime_env_file` looked
    for `.runtime/prod.env`, which the render step never writes, found nothing, and
    left `Settings` on its hardcoded defaults -- while `factory.py` and
    `validate_security_settings` both read the value as production. A deployment
    that named itself the short way ran the whole application on defaults, in
    production, with nothing saying so.

    Normalising here means the value `Settings` carries is already the long form,
    so a consumer can compare against one string and the file lookup and the field
    cannot disagree about which environment this is.
    """

    value = str(raw or "").strip().lower() or DEFAULT_ENVIRONMENT
    return _ENVIRONMENT_ALIASES.get(value, value)


def resolve_runtime_env_file() -> str | None:
    """Resolve the generated runtime environment without relying on root .env."""
    explicit = os.getenv("RUNTIME_ENV_FILE", "").strip()
    if explicit:
        return explicit
    environment = normalise_environment_name(os.getenv("APP_ENV", DEFAULT_ENVIRONMENT))
    candidate = Path(__file__).resolve().parents[2] / ".runtime" / f"{environment}.env"
    return str(candidate) if candidate.is_file() else None


def _normalised_choice(value: Any) -> Any:
    """Trim and lower-case a choice before it is matched against the allowed set.

    Every consumer of these fields already did this -- `str(...).strip().lower()`
    appears at each of them -- so normalising here keeps `MODEL_BACKEND=OpenAI`
    working while letting the field itself state what the allowed values are. It
    also makes the stored value canonical, so the `.lower()` at the call sites
    stops being load-bearing.
    """

    return value.strip().lower() if isinstance(value, str) else value


def _choice(*allowed: str) -> Any:
    """A string field that may only hold one of `allowed`.

    These sets were written in a trailing comment -- `# auto|memory|redis` -- and
    enforced nowhere, so a typo did not fail: every consumer silently fell back to
    a default. `HISTORY_BACKEND=sqlight` served files, `WEB_SEARCH_PROVIDER=tavly`
    searched DuckDuckGo, and `AUTH_COOKIE_SAMESITE=strct` quietly downgraded the
    cookie policy to `lax` -- a security setting weakened by a spelling mistake,
    with nothing anywhere reporting it.

    Stating the set on the field turns each of those into a refused write from the
    console and a loud failure at startup, and `config_schema.describe` reads the
    same set back out, so the page can offer the choices rather than a free-text
    box. One definition, in the place the value is defined.
    """

    return Annotated[Literal[allowed], BeforeValidator(_normalised_choice)]  # type: ignore[valid-type]


class Settings(BaseSettings):
    # `env_file` is deliberately NOT set here. `model_config` is evaluated once,
    # when this class body runs, so a path resolved into it is frozen for the life
    # of the process -- and `.runtime/` starts empty, so the ordinary sequence
    # (start something, then `make config-render`) left the process reading
    # defaults from a file it could see but had never loaded. `reload_settings()`
    # could not recover it either. The dotenv source is built per construction in
    # `settings_customise_sources` instead.
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Declare the precedence, once, here.

            init > real process environment > configuration centre > .runtime/*.env > defaults

        The process environment sits *above* the configuration centre on
        purpose: a deployment has to keep one way to pin a value that the
        console cannot move. `MODEL_BACKEND=local` already depends on exactly
        that, overriding persisted admin model settings.

        `RemoteSettingsSource` returns `{}` unless `NACOS_ENABLED` is true, so
        this costs an installation without a configuration centre one function
        call and no import of the SDK.

        The dotenv source is rebuilt here rather than taken from `dotenv_settings`,
        because the one handed in carries the path `model_config` froze at import.
        Resolving it per construction is what lets a reload pick up a runtime file
        that was rendered after the process started, and what stops
        `config_schema.describe` -- which resolves the path fresh -- from naming a
        file as the source of a value `Settings` never read.
        """

        from app.core.remote_config import RemoteSettingsSource

        del dotenv_settings
        return (
            init_settings,
            env_settings,
            RemoteSettingsSource(settings_cls),
            DotEnvSettingsSource(
                settings_cls,
                env_file=resolve_runtime_env_file(),
                env_file_encoding="utf-8",
            ),
            file_secret_settings,
        )

    # Not a `_choice(...)`: `resolve_runtime_env_file` will load any
    # `.runtime/<name>.env` a deployment renders by hand, so a fixed set here would
    # forbid a `staging` that works today. What is fixed is the *spelling* -- see
    # `normalise_environment_name`.
    app_env: Annotated[str, BeforeValidator(normalise_environment_name)] = Field(
        default=DEFAULT_ENVIRONMENT, alias="APP_ENV"
    )
    # The worker count the operator *declares*; it must match the launch command
    # (uvicorn --workers / gunicorn -w). Nothing can observe the real count from
    # inside one worker, so `validate_worker_topology` trusts this value.
    app_workers: int = Field(default=1, ge=1, alias="APP_WORKERS")
    # Where state that must be shared between workers lives (ARC-01). `memory`
    # keeps today's per-process stores; `shared` requires a reachable Redis at
    # startup, and each ARC-01 phase moves its stores behind this switch.
    state_backend: _choice("memory", "shared") = Field(default="memory", alias="STATE_BACKEND")
    # Namespace for every shared-state key, so two deployments sharing one Redis
    # (or a Redis shared with something else) cannot read each other's counters.
    state_key_prefix: str = Field(default="qm:", min_length=1, max_length=32, alias="STATE_KEY_PREFIX")
    # The six backends every comparison in app/ is written against, and the same
    # set `deploy/scripts/config.py::VALID_BACKENDS` validates at render time --
    # pinned against it by tests/core/test_config_choices.py.
    model_backend: _choice("openai", "anthropic", "ollama", "local", "custom", "deepseek") = Field(
        default="local", alias="MODEL_BACKEND"
    )
    reasoning_model_backend: str = Field(default="", alias="REASONING_MODEL_BACKEND")

    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="qwen3:14b", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="nomic-embed-text", alias="OLLAMA_EMBED_MODEL")
    ollama_reasoning_model: str = Field(default="deepseek-r1:32b", alias="OLLAMA_REASONING_MODEL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_chat_model: str = Field(default="gpt-5.5", alias="OPENAI_CHAT_MODEL")
    openai_embed_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBED_MODEL")
    openai_reasoning_model: str = Field(default="gpt-5.5", alias="OPENAI_REASONING_MODEL")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_chat_model: str = Field(default="claude-sonnet-5", alias="ANTHROPIC_CHAT_MODEL")
    anthropic_reasoning_model: str = Field(default="claude-fable-5", alias="ANTHROPIC_REASONING_MODEL")

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_username: str = Field(default="neo4j", alias="NEO4J_USERNAME")
    neo4j_password: str = Field(default="", alias="NEO4J_PASSWORD")

    chroma_collection: str = Field(default="local_rag_collection", alias="CHROMA_COLLECTION")
    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")
    # A Chroma server (`http://chroma:8000`). Set, every process talks to it over
    # HTTP; empty, the store is the embedded directory above, which only one
    # process may write. STATE_BACKEND=shared requires it (ARC-01 phase 5).
    chroma_server_url: str = Field(default="", alias="CHROMA_SERVER_URL")
    data_dir: str = Field(default="./data/docs", alias="DATA_DIR")
    corpus_store_path: str = Field(default="./data/chunks/chunks.jsonl", alias="CORPUS_STORE_PATH")
    parent_store_path_str: str = Field(default="./data/chunks/parents.jsonl", alias="PARENT_STORE_PATH")
    # How long a request waits for the index lock before answering 503 (ARC-01
    # phase 5). The ingest worker holds it only while writing, never while
    # parsing or embedding, so a wait longer than this is a stuck writer.
    index_lock_request_timeout_seconds: float = Field(
        default=5.0, gt=0, le=60, alias="INDEX_LOCK_REQUEST_TIMEOUT_SECONDS"
    )
    # How long one ingest or reindex job may run in the ingest worker before RQ
    # stops it and the document is marked failed (STATE_BACKEND=shared only).
    ingest_job_timeout_seconds: int = Field(default=3600, ge=60, le=86_400, alias="INGEST_JOB_TIMEOUT_SECONDS")
    evidence_artifact_root: str = Field(default="./data/evidence", alias="EVIDENCE_ARTIFACT_ROOT")
    wiki_db_path_str: str = Field(default="./data/wiki/wiki.db", alias="WIKI_DB_PATH")
    wiki_generation_timeout_ms: int = Field(default=30_000, ge=100, le=120_000, alias="WIKI_GENERATION_TIMEOUT_MS")
    wiki_scan_limit: int = Field(default=500, ge=10, le=10_000, alias="WIKI_SCAN_LIMIT")
    # Accumulated router-calibration outcomes. Runtime state, so it lives under
    # data/ rather than in the tracked config/ file the calibrator used to write
    # on every single request.
    router_calibration_path_str: str = Field(default="./data/router_calibration.json", alias="ROUTER_CALIBRATION_PATH")

    parent_chunk_size: int = Field(default=1500, alias="PARENT_CHUNK_SIZE")
    parent_chunk_overlap: int = Field(default=200, alias="PARENT_CHUNK_OVERLAP")
    child_chunk_size: int = Field(default=600, alias="CHILD_CHUNK_SIZE")
    child_chunk_overlap: int = Field(default=120, alias="CHILD_CHUNK_OVERLAP")
    table_row_overlap: int = Field(default=1, alias="TABLE_ROW_OVERLAP")

    top_k: int = Field(default=4, ge=1, le=50, alias="TOP_K")
    max_context_chunks: int = Field(default=6, ge=1, le=100, alias="MAX_CONTEXT_CHUNKS")
    bm25_top_k: int = Field(default=6, ge=1, le=100, alias="BM25_TOP_K")
    vector_top_k: int = Field(default=6, ge=1, le=100, alias="VECTOR_TOP_K")
    hybrid_rrf_k: int = Field(default=60, alias="HYBRID_RRF_K")
    hybrid_vector_weight: float = Field(default=0.95, alias="HYBRID_VECTOR_WEIGHT")
    hybrid_bm25_weight: float = Field(default=0.05, alias="HYBRID_BM25_WEIGHT")
    vector_similarity_threshold: float = Field(default=0.2, alias="VECTOR_SIMILARITY_THRESHOLD")
    vector_similarity_relaxed_threshold: float = Field(default=0.05, alias="VECTOR_SIMILARITY_RELAXED_THRESHOLD")
    query_rewrite_enabled: bool = Field(default=True, alias="QUERY_REWRITE_ENABLED")
    query_rewrite_with_llm: bool = Field(default=False, alias="QUERY_REWRITE_WITH_LLM")
    query_decompose_enabled: bool = Field(default=True, alias="QUERY_DECOMPOSE_ENABLED")
    query_expansion_enabled: bool = Field(default=True, alias="QUERY_EXPANSION_ENABLED")
    query_expansion_max_ratio: float = Field(default=3.0, alias="QUERY_EXPANSION_MAX_RATIO")
    rank_feature_enabled: bool = Field(default=True, alias="RANK_FEATURE_ENABLED")
    rank_feature_source_weight: float = Field(default=0.08, alias="RANK_FEATURE_SOURCE_WEIGHT")
    rank_feature_freshness_weight: float = Field(default=0.07, alias="RANK_FEATURE_FRESHNESS_WEIGHT")
    rank_feature_retrieval_diversity_weight: float = Field(
        default=0.05, alias="RANK_FEATURE_RETRIEVAL_DIVERSITY_WEIGHT"
    )
    dynamic_retrieval_enabled: bool = Field(default=True, alias="DYNAMIC_RETRIEVAL_ENABLED")
    dynamic_vector_top_k_cap: int = Field(default=16, alias="DYNAMIC_VECTOR_TOP_K_CAP")
    dynamic_bm25_top_k_cap: int = Field(default=16, alias="DYNAMIC_BM25_TOP_K_CAP")
    dynamic_reranker_top_n_cap: int = Field(default=10, alias="DYNAMIC_RERANKER_TOP_N_CAP")

    # Folded in from module-level `os.getenv` reads on 2026-09-01.  Those were
    # unreachable by the documented config flow: pydantic-settings loads
    # `.runtime/{APP_ENV}.env` into Settings without exporting anything into the
    # process environment, so a key read with `os.getenv` could only ever be set
    # as a real exported variable -- and none of these appear in `config/env/`.
    # Anything a config centre is meant to manage has to be a field here first.
    enable_calibration: bool = Field(default=False, alias="ENABLE_CALIBRATION")
    enable_web_route_downgrade: bool = Field(default=False, alias="ENABLE_WEB_ROUTE_DOWNGRADE")
    self_rag_relevance_threshold: float = Field(default=0.6, ge=0.0, le=1.0, alias="SELF_RAG_RELEVANCE_THRESHOLD")
    self_rag_quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0, alias="SELF_RAG_QUALITY_THRESHOLD")
    request_metrics_maxlen: int = Field(default=1000, alias="REQUEST_METRICS_MAXLEN")
    strict_csp: bool = Field(default=False, alias="STRICT_CSP")

    # Migrated out of `app/agents/shared/config.py` on 2026-09-01, where they
    # were module constants read with `os.getenv` at import time -- settable
    # only as exported environment variables, and invisible to the render step
    # and to the configuration centre. Every one of them is read on the request
    # path through `app/agents/verifier/validation/`.
    answer_approve_threshold: float = Field(default=0.80, alias="ANSWER_APPROVE_THRESHOLD")
    answer_flag_threshold: float = Field(default=0.60, alias="ANSWER_FLAG_THRESHOLD")
    hallucination_high_risk_threshold: float = Field(default=0.30, alias="HALLUCINATION_HIGH_RISK_THRESHOLD")
    nli_model_name: str = Field(default="cross-encoder/nli-MiniLM2-L6-H768", alias="NLI_MODEL_NAME")
    nli_max_sentences: int = Field(default=5, ge=1, le=100, alias="NLI_MAX_SENTENCES")
    cascade_enable_rules: bool = Field(default=True, alias="CASCADE_ENABLE_RULES")
    cascade_enable_nli: bool = Field(default=True, alias="CASCADE_ENABLE_NLI")
    cascade_enable_citations: bool = Field(default=True, alias="CASCADE_ENABLE_CITATIONS")
    cascade_enable_deep: bool = Field(default=True, alias="CASCADE_ENABLE_DEEP")
    cascade_nli_timeout_ms: int = Field(default=1200, ge=100, le=60_000, alias="CASCADE_NLI_TIMEOUT_MS")
    cascade_deep_timeout_ms: int = Field(default=3000, ge=100, le=60_000, alias="CASCADE_DEEP_TIMEOUT_MS")
    retrieval_cache_enabled: bool = Field(default=True, alias="RETRIEVAL_CACHE_ENABLED")
    retrieval_cache_ttl_seconds: int = Field(default=45, ge=1, le=86_400, alias="RETRIEVAL_CACHE_TTL_SECONDS")
    retrieval_cache_max_items: int = Field(default=256, alias="RETRIEVAL_CACHE_MAX_ITEMS")
    circuit_breaker_enabled: bool = Field(default=True, alias="CIRCUIT_BREAKER_ENABLED")
    circuit_breaker_fail_threshold: int = Field(default=5, alias="CIRCUIT_BREAKER_FAIL_THRESHOLD")
    circuit_breaker_cooldown_seconds: int = Field(default=60, alias="CIRCUIT_BREAKER_COOLDOWN_SECONDS")
    # `off`, `none` and `disabled` are three spellings of the same thing in
    # `retrievers/hybrid/caching.py::cache_backend`; the comment here used to
    # name only the first, so two working values read as typos.
    retrieval_cache_backend: _choice("auto", "memory", "redis", "off", "none", "disabled") = Field(
        default="auto", alias="RETRIEVAL_CACHE_BACKEND"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Session metadata storage backend
    session_metadata_backend: _choice("database", "memory") = Field(
        default="database", alias="SESSION_METADATA_BACKEND"
    )
    long_term_memory_enabled: bool = Field(default=True, alias="LONG_TERM_MEMORY_ENABLED")
    long_term_memory_max_items: int = Field(default=100, ge=1, le=10_000, alias="LONG_TERM_MEMORY_MAX_ITEMS")
    memory_task_ttl_days: int = Field(default=30, ge=1, le=3650, alias="MEMORY_TASK_TTL_DAYS")
    memory_stable_fact_ttl_days: int = Field(default=365, ge=1, le=3650, alias="MEMORY_STABLE_FACT_TTL_DAYS")

    # Multi-modal Processing
    ocr_engine: str = Field(default="tesseract", alias="OCR_ENGINE")  # tesseract|paddleocr
    multimodal_fusion_method: _choice("rrf", "weighted") = Field(default="rrf", alias="MULTIMODAL_FUSION_METHOD")
    image_weight: float = Field(default=0.3, alias="IMAGE_WEIGHT")
    table_weight: float = Field(default=0.3, alias="TABLE_WEIGHT")
    text_weight: float = Field(default=0.4, alias="TEXT_WEIGHT")

    # Performance Optimization - Caching
    cache_l2_enabled: bool = Field(default=False, alias="CACHE_L2_ENABLED")
    cache_l1_size: int = Field(default=256, alias="CACHE_L1_SIZE")
    cache_l1_ttl: int = Field(default=300, alias="CACHE_L1_TTL")  # 5 minutes
    cache_l2_ttl: int = Field(default=3600, alias="CACHE_L2_TTL")  # 1 hour

    # Performance Optimization - Database

    # Performance Optimization - Retrieval

    # Advanced Reasoning - Tool Runner

    database_url: str = Field(default="sqlite:///./data/querymind.db", alias="DATABASE_URL")
    sqlite_busy_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=3600.0,
        alias="SQLITE_BUSY_TIMEOUT_SECONDS",
    )

    otel_tracing_enabled: bool = Field(default=True, alias="OTEL_TRACING_ENABLED")
    slo_p95_latency_ms_threshold: int = Field(default=3000, alias="SLO_P95_LATENCY_MS_THRESHOLD")
    slo_error_rate_percent_threshold: float = Field(default=5.0, alias="SLO_ERROR_RATE_PERCENT_THRESHOLD")
    slo_grounding_support_ratio_threshold: float = Field(default=0.6, alias="SLO_GROUNDING_SUPPORT_RATIO_THRESHOLD")
    consistency_guard_enabled: bool = Field(default=True, alias="CONSISTENCY_GUARD_ENABLED")
    web_search_on_empty_corpus: bool = Field(default=True, alias="WEB_SEARCH_ON_EMPTY_CORPUS")
    """Search the web when the caller has no documents to search instead.

    A caller with an empty document scope cannot get an answer from local
    retrieval -- there is nothing there -- so without this the only possible
    outcome is the "no evidence" message, on every question, for every account
    that has not uploaded anything yet. That is the state every new account
    starts in.

    It defaults on because the alternative is refusing a question the system
    could answer, and because the question already reaches the same search
    backend on the `web` route with no separate opt-in. It is a switch rather
    than a constant because it is a *policy*: it sends the user's question to a
    third party (DuckDuckGo, via `app/tools/web/search.py`), and a deployment
    that must not reach the internet has to be able to say so in one place.
    `run_web_research` redacts sensitive patterns from the question first.
    """

    web_domain_allowlist: str = Field(
        default="gov.cn,gov,edu,org,nist.gov,cisa.gov,mitre.org,wikipedia.org,owasp.org,microsoft.com,openai.com,python.org,github.com,realpython.com,stackoverflow.com,pypi.org",
        alias="WEB_DOMAIN_ALLOWLIST",
    )
    web_min_source_score: float = Field(default=0.2, ge=0.0, le=1.0, alias="WEB_MIN_SOURCE_SCORE")
    web_search_provider: _choice("duckduckgo", "tavily", "bing", "searxng") = Field(
        default="duckduckgo", alias="WEB_SEARCH_PROVIDER"
    )
    web_proxy_url: str | None = Field(default=None, alias="WEB_PROXY_URL")
    web_search_timeout_seconds: int = Field(default=15, ge=1, le=120, alias="WEB_SEARCH_TIMEOUT_SECONDS")
    web_search_max_retries: int = Field(default=2, ge=0, le=10, alias="WEB_SEARCH_MAX_RETRIES")
    web_strict_allowlist: bool = Field(default=True, alias="WEB_STRICT_ALLOWLIST")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    bing_search_api_key: str | None = Field(default=None, alias="BING_SEARCH_API_KEY")
    searxng_base_url: str | None = Field(default=None, alias="SEARXNG_BASE_URL")
    answer_safety_scan_enabled: bool = Field(default=True, alias="ANSWER_SAFETY_SCAN_ENABLED")
    prompt_injection_defense_enabled: bool = Field(default=True, alias="PROMPT_INJECTION_DEFENSE_ENABLED")
    prompt_injection_strict_mode: bool = Field(default=True, alias="PROMPT_INJECTION_STRICT_MODE")
    prompt_injection_risk_threshold: float = Field(default=0.7, alias="PROMPT_INJECTION_RISK_THRESHOLD")

    enable_reranker: bool = Field(default=True, alias="ENABLE_RERANKER")
    reranker_model_name: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL_NAME")
    # The local semantic embedding model, used when MODEL_BACKEND is `local` and
    # no administrator configuration supplies an embedding provider. Loaded with
    # `local_files_only=True` like the reranker, so an absent model degrades to
    # `LocalHashEmbeddings` rather than starting a download inside a request.
    #
    # CHANGING THIS REQUIRES A REINDEX. Embedding dimensions differ between
    # models (hash is 384, bge-m3 is 1024) and a Chroma collection is
    # dimension-locked, so an existing store must be rebuilt.
    local_embed_model: str = Field(default="BAAI/bge-m3", alias="LOCAL_EMBED_MODEL")
    reranker_top_n: int = Field(default=5, ge=1, le=50, alias="RERANKER_TOP_N")

    # LLM-powered features
    query_rewrite_max_variants: int = Field(default=3, alias="QUERY_REWRITE_MAX_VARIANTS")

    graph_extraction_mode: str = Field(default="llm", alias="GRAPH_EXTRACTION_MODE")
    graph_triplet_batch_chars: int = Field(default=2200, alias="GRAPH_TRIPLET_BATCH_CHARS")
    graph_rag_enhanced: bool = Field(default=False, alias="GRAPH_RAG_ENHANCED")
    graph_rag_min_pdf_quality: float = Field(default=0.3, alias="GRAPH_RAG_MIN_PDF_QUALITY")
    graph_entity_extraction_robust: bool = Field(default=True, alias="GRAPH_ENTITY_EXTRACTION_ROBUST")
    graph_entity_extraction_use_llm: bool = Field(default=False, alias="GRAPH_ENTITY_EXTRACTION_USE_LLM")

    pdf_loader_mode: _choice("pypdf", "docling", "docling_enhanced", "docling_advanced", "hybrid") = Field(
        default="pypdf", alias="PDF_LOADER_MODE"
    )
    pdf_enable_cleaning: bool = Field(default=True, alias="PDF_ENABLE_CLEANING")  # Remove headers/footers
    pdf_enable_table_merging: bool = Field(default=True, alias="PDF_ENABLE_TABLE_MERGING")  # Merge cross-page tables
    pdf_enable_chart_extraction: bool = Field(
        default=False, alias="PDF_ENABLE_CHART_EXTRACTION"
    )  # Extract charts with vision
    pdf_chart_vision_model: str = Field(default="gpt-4o", alias="PDF_CHART_VISION_MODEL")  # gpt-4o|claude-opus-4-8
    pdf_enable_structure_analysis: bool = Field(
        default=False, alias="PDF_ENABLE_STRUCTURE_ANALYSIS"
    )  # Document structure
    pdf_enable_coreference: bool = Field(default=False, alias="PDF_ENABLE_COREFERENCE")  # Pronoun resolution
    pdf_enable_formula_enrichment: bool = Field(
        default=False, alias="PDF_ENABLE_FORMULA_ENRICHMENT"
    )  # Formula semantics

    sessions_dir: str = Field(default="./data/sessions", alias="SESSIONS_DIR")
    uploads_dir: str = Field(default="./data/uploads", alias="UPLOADS_DIR")
    auto_ingest_enabled: bool = Field(default=False, alias="AUTO_INGEST_ENABLED")
    auto_ingest_interval_seconds: float = Field(default=3.0, alias="AUTO_INGEST_INTERVAL_SECONDS")
    auto_ingest_watch_docs: bool = Field(default=True, alias="AUTO_INGEST_WATCH_DOCS")
    auto_ingest_watch_uploads: bool = Field(default=True, alias="AUTO_INGEST_WATCH_UPLOADS")
    auto_ingest_recursive: bool = Field(default=True, alias="AUTO_INGEST_RECURSIVE")
    auth_token_ttl_hours: int = Field(default=24, alias="AUTH_TOKEN_TTL_HOURS")
    auth_expose_token_in_response: bool = Field(default=False, alias="AUTH_EXPOSE_TOKEN_IN_RESPONSE")
    auth_cookie_name: str = Field(default="auth_token", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=True, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: _choice("strict", "lax", "none") = Field(default="strict", alias="AUTH_COOKIE_SAMESITE")
    app_db_path_str: str = Field(default="./data/app.db", alias="APP_DB_PATH")

    auth_login_max_failures: int = Field(default=8, alias="AUTH_LOGIN_MAX_FAILURES")
    auth_login_window_seconds: int = Field(default=300, alias="AUTH_LOGIN_WINDOW_SECONDS")
    auth_register_max_attempts: int = Field(default=12, alias="AUTH_REGISTER_MAX_ATTEMPTS")
    auth_register_window_seconds: int = Field(default=300, alias="AUTH_REGISTER_WINDOW_SECONDS")

    # OAuth Configuration
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/google/callback", alias="OAUTH_REDIRECT_URI"
    )

    query_rate_limit_max_attempts: int = Field(default=30, alias="QUERY_RATE_LIMIT_MAX_ATTEMPTS")
    query_rate_limit_window_seconds: int = Field(default=60, alias="QUERY_RATE_LIMIT_WINDOW_SECONDS")
    # Role-based rate limiting (v0.4.5+)
    query_guard_backend: _choice("auto", "memory", "redis") = Field(default="auto", alias="QUERY_GUARD_BACKEND")
    query_max_concurrent: int = Field(default=24, alias="QUERY_MAX_CONCURRENT")
    query_max_waiting: int = Field(default=120, alias="QUERY_MAX_WAITING")
    query_acquire_timeout_ms: int = Field(default=3000, alias="QUERY_ACQUIRE_TIMEOUT_MS")
    shadow_queue_workers: int = Field(default=2, alias="SHADOW_QUEUE_WORKERS")
    shadow_queue_maxsize: int = Field(default=200, alias="SHADOW_QUEUE_MAXSIZE")
    synthesis_refine_max_rounds: int = Field(default=5, alias="SYNTHESIS_REFINE_MAX_ROUNDS")
    synthesis_refine_overload_rounds: int = Field(default=1, alias="SYNTHESIS_REFINE_OVERLOAD_ROUNDS")
    history_backend: _choice("file", "sqlite") = Field(default="file", alias="HISTORY_BACKEND")
    history_sqlite_path_str: str = Field(default="./data/history.db", alias="HISTORY_SQLITE_PATH")
    history_cold_dir: str = Field(default="./data/sessions_cold", alias="HISTORY_COLD_DIR")
    history_hot_tier_days: int = Field(default=14, alias="HISTORY_HOT_TIER_DAYS")
    bulkhead_enabled: bool = Field(default=True, alias="BULKHEAD_ENABLED")
    bulkhead_llm_max_concurrent: int = Field(default=12, alias="BULKHEAD_LLM_MAX_CONCURRENT")
    bulkhead_neo4j_max_concurrent: int = Field(default=20, alias="BULKHEAD_NEO4J_MAX_CONCURRENT")
    bulkhead_web_max_concurrent: int = Field(default=8, alias="BULKHEAD_WEB_MAX_CONCURRENT")
    bulkhead_acquire_timeout_ms: int = Field(default=1500, alias="BULKHEAD_ACQUIRE_TIMEOUT_MS")
    alerting_enabled: bool = Field(default=False, alias="ALERTING_ENABLED")
    alert_webhook_url: str = Field(default="", alias="ALERT_WEBHOOK_URL")
    alert_webhook_allowlist: str = Field(default="", alias="ALERT_WEBHOOK_ALLOWLIST")  # csv domains
    alert_min_interval_seconds: int = Field(default=60, alias="ALERT_MIN_INTERVAL_SECONDS")
    alert_slack_webhook_url: str = Field(default="", alias="ALERT_SLACK_WEBHOOK_URL")
    alert_email_smtp_host: str = Field(default="", alias="ALERT_EMAIL_SMTP_HOST")
    alert_email_smtp_port: int = Field(default=587, alias="ALERT_EMAIL_SMTP_PORT")
    alert_email_smtp_username: str = Field(default="", alias="ALERT_EMAIL_SMTP_USERNAME")
    alert_email_smtp_password: str = Field(default="", alias="ALERT_EMAIL_SMTP_PASSWORD")
    alert_email_use_tls: bool = Field(default=True, alias="ALERT_EMAIL_USE_TLS")
    alert_email_from: str = Field(default="", alias="ALERT_EMAIL_FROM")
    alert_email_to: str = Field(default="", alias="ALERT_EMAIL_TO")  # csv recipients
    response_signing_enabled: bool = Field(default=True, alias="RESPONSE_SIGNING_ENABLED")
    response_signing_secret: str = Field(default="", alias="RESPONSE_SIGNING_SECRET")
    response_signing_active_kid: str = Field(default="v1", alias="RESPONSE_SIGNING_ACTIVE_KID")
    response_signing_keys: str = Field(
        default="", alias="RESPONSE_SIGNING_KEYS"
    )  # semicolon-separated pairs of key ID and secret
    api_settings_encryption_key: str = Field(default="", alias="API_SETTINGS_ENCRYPTION_KEY")
    api_base_url_allowlist: str = Field(default="", alias="API_BASE_URL_ALLOWLIST")  # csv host suffixes
    api_base_url_allow_private: bool = Field(default=False, alias="API_BASE_URL_ALLOW_PRIVATE")
    api_base_url_dns_check: bool = Field(default=True, alias="API_BASE_URL_DNS_CHECK")
    outbound_llm_redaction_enabled: bool = Field(default=True, alias="OUTBOUND_LLM_REDACTION_ENABLED")
    outbound_embedding_redaction_enabled: bool = Field(default=True, alias="OUTBOUND_EMBEDDING_REDACTION_ENABLED")
    outbound_redaction_custom_terms: str = Field(default="", alias="OUTBOUND_REDACTION_CUSTOM_TERMS")
    outbound_redaction_custom_regexes: str = Field(default="", alias="OUTBOUND_REDACTION_CUSTOM_REGEXES")
    quota_enabled: bool = Field(default=False, alias="QUOTA_ENABLED")
    quota_query_max_per_minute: int = Field(default=120, alias="QUOTA_QUERY_MAX_PER_MINUTE")
    quota_web_max_per_minute: int = Field(default=30, alias="QUOTA_WEB_MAX_PER_MINUTE")
    quota_mode: _choice("user", "business_unit") = Field(default="user", alias="QUOTA_MODE")
    feature_flags: str = Field(default="", alias="FEATURE_FLAGS")  # name=on|off|pct:10
    feature_flag_seed: str = Field(default="feature", alias="FEATURE_FLAG_SEED")
    verifier_max_retries: int = Field(default=1, ge=0, le=1, alias="VERIFIER_MAX_RETRIES")
    # How many tool hops one request may take. Each hop is a model call plus a
    # governed invocation, and the whole loop shares one STAGE_TIMEOUT_TOOL_MS
    # ceiling, so this bounds cost rather than latency.
    tool_max_steps: int = Field(default=3, ge=1, le=8, alias="TOOL_MAX_STEPS")
    # How much of retrieval has to succeed before an answer is worth attempting.
    # 1 keeps the default "any source is enough"; a higher number, or a list of
    # sources that must not fail, selects the stricter policies in
    # app/agents/rag/service.py.
    retrieval_min_successful_sources: int = Field(default=1, ge=1, le=8, alias="RETRIEVAL_MIN_SUCCESSFUL_SOURCES")
    retrieval_required_sources: str = Field(default="", alias="RETRIEVAL_REQUIRED_SOURCES")
    # Post-generation groundedness checking. Off by default: it is an extra LLM
    # round trip per answer, which is a cost decision rather than a correctness
    # one. It now actually works when switched on -- it used to verify against an
    # empty source list, see app/agents/synthesizer/generation.py.
    answer_fact_verification_enabled: bool = Field(default=False, alias="ANSWER_FACT_VERIFICATION_ENABLED")
    # Orchestration stage ceilings. These bound a hang; they are not latency
    # targets (the P95 target is seconds, see CLAUDE.md "Quality Metrics"). The
    # previous values were tight enough that an ordinary slow LLM call tripped
    # them, and a tripped stage was an unconditional 500. Read by
    # app/orchestration/timeout_control.py::TimeoutConfig.from_settings.
    stage_timeout_total_ms: int = Field(default=120_000, ge=5_000, le=600_000, alias="STAGE_TIMEOUT_TOTAL_MS")
    stage_timeout_route_ms: int = Field(default=8_000, ge=500, le=120_000, alias="STAGE_TIMEOUT_ROUTE_MS")
    stage_timeout_plan_ms: int = Field(default=5_000, ge=500, le=120_000, alias="STAGE_TIMEOUT_PLAN_MS")
    stage_timeout_retrieval_ms: int = Field(default=30_000, ge=500, le=120_000, alias="STAGE_TIMEOUT_RETRIEVAL_MS")
    stage_timeout_tool_ms: int = Field(default=10_000, ge=500, le=120_000, alias="STAGE_TIMEOUT_TOOL_MS")
    stage_timeout_synthesis_ms: int = Field(default=30_000, ge=500, le=120_000, alias="STAGE_TIMEOUT_SYNTHESIS_MS")
    stage_timeout_finalization_ms: int = Field(default=8_000, ge=500, le=120_000, alias="STAGE_TIMEOUT_FINALIZATION_MS")
    stage_timeout_overhead_ms: int = Field(default=2_000, ge=0, le=60_000, alias="STAGE_TIMEOUT_OVERHEAD_MS")
    # Wall-clock ceiling handed to the LLM HTTP client. Without one, a hung
    # provider connection pins a pool thread forever: the stage timeout unblocks
    # the event loop but cannot cancel the thread doing the blocking call.
    llm_request_timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0, alias="LLM_REQUEST_TIMEOUT_SECONDS")
    langgraph_recursion_limit: int = Field(default=20, ge=12, le=100, alias="LANGGRAPH_RECURSION_LIMIT")
    planner_max_tasks: int = Field(default=8, ge=1, le=32, alias="PLANNER_MAX_TASKS")
    planner_max_depth: int = Field(default=4, ge=1, le=16, alias="PLANNER_MAX_DEPTH")
    planner_max_retrieval_budget: int = Field(default=16, ge=1, le=128, alias="PLANNER_MAX_RETRIEVAL_BUDGET")
    planner_max_tool_budget: int = Field(default=4, ge=0, le=32, alias="PLANNER_MAX_TOOL_BUDGET")
    knowledge_source_timeout_ms: int = Field(default=10_000, ge=100, le=120_000, alias="KNOWLEDGE_SOURCE_TIMEOUT_MS")
    knowledge_max_sources: int = Field(default=6, ge=1, le=8, alias="KNOWLEDGE_MAX_SOURCES")
    knowledge_context_token_budget: int = Field(
        default=8_000,
        ge=256,
        le=128_000,
        alias="KNOWLEDGE_CONTEXT_TOKEN_BUDGET",
    )
    knowledge_reranker_timeout_ms: int = Field(
        default=10_000,
        ge=100,
        le=120_000,
        alias="KNOWLEDGE_RERANKER_TIMEOUT_MS",
    )
    # Only the hash. ADMIN_CREATE_APPROVAL_TOKEN is a render-time input to
    # deploy/scripts/config.py, which derives this hash into .runtime/*.env; the
    # plaintext deliberately never reaches the application.
    admin_create_approval_token_hash: str = Field(default="", alias="ADMIN_CREATE_APPROVAL_TOKEN_HASH")

    upload_max_files: int = Field(default=20, alias="UPLOAD_MAX_FILES")
    upload_max_file_bytes: int = Field(default=20 * 1024 * 1024, alias="UPLOAD_MAX_FILE_BYTES")
    upload_max_total_bytes: int = Field(default=100 * 1024 * 1024, alias="UPLOAD_MAX_TOTAL_BYTES")
    upload_read_chunk_bytes: int = Field(default=1024 * 1024, alias="UPLOAD_READ_CHUNK_BYTES")
    tesseract_cmd: str = Field(default="", alias="TESSERACT_CMD")
    tesseract_lang: str = Field(default="chi_sim+eng", alias="TESSERACT_LANG")
    tessdata_prefix: str = Field(default="", alias="TESSDATA_PREFIX")
    ocr_preprocess_enabled: bool = Field(default=True, alias="OCR_PREPROCESS_ENABLED")
    ocr_upscale_min_side: int = Field(default=1200, alias="OCR_UPSCALE_MIN_SIDE")
    ocr_psm_modes: str = Field(default="6,11,3", alias="OCR_PSM_MODES")
    image_caption_enabled: bool = Field(default=False, alias="IMAGE_CAPTION_ENABLED")
    image_caption_backend: _choice("auto", "openai", "ollama") = Field(default="auto", alias="IMAGE_CAPTION_BACKEND")
    openai_vision_model: str = Field(default="gpt-4o", alias="OPENAI_VISION_MODEL")
    ollama_vision_model: str = Field(default="llama4-scout:8b", alias="OLLAMA_VISION_MODEL")
    cors_enabled: bool = Field(default=True, alias="CORS_ENABLED")
    cors_allow_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174,http://127.0.0.1:5175,http://localhost:5175,http://127.0.0.1:8000,http://localhost:8000",
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_methods: str = Field(default="*", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="*", alias="CORS_ALLOW_HEADERS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")

    @model_validator(mode="after")
    def _stage_ceilings_fit_the_total(self) -> "Settings":
        """One pass of every stage has to fit inside the whole-request budget.

        `TimeoutConfig.validate()` has always enforced this, and it runs from
        `TimeoutConfig.from_settings`, which `get_timeout_config` calls **per
        request**. So the rule was checked in the one place where breaking it is
        an outage rather than a refusal: each stage ceiling carries its own
        `ge/le`, seven of them are editable, and each is satisfiable while their
        sum is not. An administrator raising `STAGE_TIMEOUT_SYNTHESIS_MS` from
        30s to 60s -- inside its own bounds -- took the sum to 123s against a
        120s total, the save was accepted, the reload succeeded, and every
        subsequent query raised out of the engine.

        Enforcing it on `Settings` moves that from a per-request failure to a
        refused write, and covers startup too: a rendered runtime file or a
        configuration-centre document with the same shape now fails loudly at
        construction instead of answering questions until the first query.

        The arithmetic is duplicated rather than imported -- `app/core` must not
        depend on `app/orchestration` -- so
        `tests/core/test_stage_budget_is_consistent.py` asserts the two agree on
        generated inputs rather than describing that they should.
        """

        stage_sum = (
            self.stage_timeout_route_ms
            + self.stage_timeout_plan_ms
            + self.stage_timeout_retrieval_ms
            + self.stage_timeout_tool_ms
            + self.stage_timeout_synthesis_ms
            + self.stage_timeout_finalization_ms
            + self.stage_timeout_overhead_ms
        )
        if stage_sum > self.stage_timeout_total_ms:
            raise ValueError(
                f"the stage ceilings add up to {stage_sum}ms, which does not fit inside "
                f"STAGE_TIMEOUT_TOTAL_MS ({self.stage_timeout_total_ms}ms); raise the total "
                f"or lower a stage"
            )
        # The per-source bound has to stay under the stage that contains it, or it
        # can never fire -- which is the state this repository already fixed once,
        # when it was a hardcoded 30s under a 10s ceiling. Both are editable, so
        # the pairing is reachable from the console.
        if self.knowledge_source_timeout_ms > self.stage_timeout_retrieval_ms:
            raise ValueError(
                f"KNOWLEDGE_SOURCE_TIMEOUT_MS ({self.knowledge_source_timeout_ms}ms) bounds one "
                f"retrieval source and must stay under STAGE_TIMEOUT_RETRIEVAL_MS "
                f"({self.stage_timeout_retrieval_ms}ms), or it can never fire"
            )
        return self

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_persist_dir)

    @property
    def docs_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def corpus_path(self) -> Path:
        return Path(self.corpus_store_path)

    @property
    def parent_store_path(self) -> Path:
        return Path(self.parent_store_path_str)

    @property
    def evidence_artifact_path(self) -> Path:
        return Path(self.evidence_artifact_root)

    @property
    def wiki_db_path(self) -> Path:
        return Path(self.wiki_db_path_str)

    @property
    def sessions_path(self) -> Path:
        return Path(self.sessions_dir)

    @property
    def uploads_path(self) -> Path:
        return Path(self.uploads_dir)

    @property
    def router_calibration_path(self) -> Path:
        return Path(self.router_calibration_path_str)

    @property
    def app_db_path(self) -> Path:
        return Path(self.app_db_path_str)

    @property
    def history_sqlite_path(self) -> Path:
        return Path(self.history_sqlite_path_str)

    @property
    def history_cold_path(self) -> Path:
        return Path(self.history_cold_dir)

    @property
    def cors_origins(self) -> list[str]:
        raw = str(self.cors_allow_origins or "").strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def cors_methods(self) -> list[str]:
        raw = str(self.cors_allow_methods or "").strip()
        if not raw:
            return ["*"]
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def cors_headers(self) -> list[str]:
        raw = str(self.cors_allow_headers or "").strip()
        if not raw:
            return ["*"]
        return [x.strip() for x in raw.split(",") if x.strip()]


def resolve_response_signing_secret(settings: Settings) -> tuple[str | None, str | None]:
    """Resolve the active response-signing key from one explicit settings snapshot."""
    active_kid = str(settings.response_signing_active_kid or "v1").strip() or "v1"
    mapping: dict[str, str] = {}
    for pair in str(settings.response_signing_keys or "").split(";"):
        if ":" not in pair:
            continue
        kid, secret = pair.split(":", 1)
        if kid.strip() and secret.strip():
            mapping[kid.strip()] = secret.strip()
    if active_kid in mapping:
        return active_kid, mapping[active_kid]
    legacy_secret = str(settings.response_signing_secret or "").strip()
    return (active_kid, legacy_secret) if legacy_secret else (None, None)


def validate_security_settings(settings: Settings) -> None:
    """Fail closed for missing production signing keys and warn elsewhere."""
    if not settings.response_signing_enabled:
        return
    kid, secret = resolve_response_signing_secret(settings)
    if kid and secret:
        return
    message = "response signing is enabled but no active signing key is configured"
    # One spelling reaches this, because the field normalises it.
    if settings.app_env == "production":
        raise RuntimeError(message)
    logger.warning("%s; responses and audit events will be unsigned", message)


def validate_worker_topology(settings: Settings) -> None:
    """Refuse several workers unless their state is shared (ARC-01).

    With STATE_BACKEND=shared every piece of state that has to agree across
    workers lives in Redis, SQLite, the Chroma server or the single
    ingest-worker (phases 1-8), so APP_WORKERS may be raised. In memory mode each
    worker would keep its own limits, sessions and indexes -- the defect ARC-01
    exists for -- so more than one is still refused.

    APP_WORKERS is the count gunicorn starts (deploy/gunicorn.conf.py reads the
    same variable), so the declared and the actual number cannot disagree.
    """
    if settings.app_workers > 1 and settings.state_backend != "shared":
        raise RuntimeError(
            f"APP_WORKERS={settings.app_workers} needs STATE_BACKEND=shared: in memory mode each "
            "worker keeps its own limits, sessions and indexes. "
            "See docs/querymind-deep-dive/arc-01-plan.html."
        )


# What STATE_BACKEND=shared requires of each per-user store, and why the other
# choice cannot be shared. Both are process-local by construction, so a worker
# running one would silently keep its own copy -- the defect ARC-01 exists for.
_SHARED_STORE_REQUIREMENTS = (
    ("history_backend", "HISTORY_BACKEND", "sqlite", "the file backend serializes writes with a threading lock"),
    (
        "session_metadata_backend",
        "SESSION_METADATA_BACKEND",
        "database",
        "the memory backend keeps session metadata in this process only",
    ),
)


def _missing_chroma_server(settings: Settings) -> list[str]:
    if str(settings.chroma_server_url or "").strip():
        return []
    return ["CHROMA_SERVER_URL (the embedded store under CHROMA_PERSIST_DIR is written by one process only)"]


def validate_shared_state_backends(settings: Settings) -> None:
    """With STATE_BACKEND=shared, refuse a store that can only be per process.

    Refused rather than overridden: quietly switching HISTORY_BACKEND to sqlite
    would hide every session an operator kept in files until they migrate them
    (`scripts/migrate_sessions_to_sqlite.py`), which reads as data loss.
    """
    if settings.state_backend != "shared":
        return
    problems = [
        f"{alias}={required} ({reason})"
        for field, alias, required, reason in _SHARED_STORE_REQUIREMENTS
        if getattr(settings, field) != required
    ]
    problems.extend(_missing_chroma_server(settings))
    if problems:
        raise RuntimeError("STATE_BACKEND=shared requires " + "; ".join(problems))


# Handed from `reload_settings` to `get_settings`, so a reload constructs
# `Settings` once. See `reload_settings` for why that is worth a module global.
_RELOAD_LOCK = threading.Lock()
_PENDING: Settings | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    global _PENDING
    settings = _PENDING if _PENDING is not None else Settings()
    _PENDING = None
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    settings.docs_path.mkdir(parents=True, exist_ok=True)
    settings.corpus_path.parent.mkdir(parents=True, exist_ok=True)
    settings.parent_store_path.parent.mkdir(parents=True, exist_ok=True)
    settings.sessions_path.mkdir(parents=True, exist_ok=True)
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    settings.app_db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.history_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    settings.history_cold_path.mkdir(parents=True, exist_ok=True)
    return settings


def reload_settings() -> Settings:
    """Re-read the configuration, validate it, and install exactly what was validated.

    Two things were wrong with the obvious four lines this replaces. It built
    `Settings` **twice** -- once to validate and once inside `get_settings()` --
    and every construction consults the configuration centre, so a reload cost two
    network round trips per data id where it needed one; with the default 3s
    timeout and several data ids that is seconds of blocking inside a request
    handler. And the object returned was not the object that had been checked: the
    documents can change between the two constructions, so the process could end
    up running settings `validate_security_settings` had never seen.

    The candidate is therefore handed to `get_settings()` rather than rebuilt.
    Validation still happens before the cache is touched, so a configuration that
    fails leaves the previous one in place -- which is the property worth keeping,
    since this is reachable from an HTTP request.
    """

    global _PENDING
    with _RELOAD_LOCK:
        candidate = Settings()
        validate_security_settings(candidate)
        _PENDING = candidate
        get_settings.cache_clear()
        try:
            return get_settings()
        finally:
            _PENDING = None
