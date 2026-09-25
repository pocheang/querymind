"""Process-level in-memory state inventory for ARC-01 Phase 0.

This inventory classifies all discovered process-level states into four categories:
- A: Must migrate before multi-worker (causes severe correctness issues or data loss)
- B: Must coordinate invalidation or sync (caches that go stale when updated)
- C: Singleton background worker / singleton role (must only run once across cluster)
- D: Safe to duplicate across workers (local read-only or harmless per-worker stats)
"""

from typing import Literal

Category = Literal["A", "B", "C", "D"]

INVENTORY: dict[str, tuple[Category, str]] = {
    "app/agents/clarification/rules.py::_OPTIMIZATION_RULE": (
        "D",
        "优化意图正则匹配只读规则对象，无运行时可变状态，多 worker 各自独立持有",
    ),
    "app/agents/clarification/rules.py::_SETUP_RULE": (
        "D",
        "环境配置意图正则匹配只读规则对象，无运行时可变状态，多 worker 各自独立持有",
    ),
    "app/agents/clarification/rules.py::_TROUBLESHOOTING_RULE": (
        "D",
        "排错意图正则匹配只读规则对象，无运行时可变状态，多 worker 各自独立持有",
    ),
    "app/agents/clarification/rules.py::_USAGE_RULE": (
        "D",
        "使用指导意图正则匹配只读规则对象，无运行时可变状态，多 worker 各自独立持有",
    ),
    "app/agents/knowledge/service.py::_word_pattern": (
        "D",
        "纯计算正则模式编译结果缓存，各进程可独立保留且无任何状态副作用",
    ),
    "app/agents/rag/cache.py::_document_context_cache": (
        "D",
        "文档内容与元数据哈希的上下文分析纯函数缓存，各 worker 独立保留无数据一致性影响",
    ),
    "app/agents/rag/cache.py::_entity_extraction_cache": (
        "D",
        "纯文本哈希的实体提取纯函数计算结果缓存，无外部状态依赖，多 worker 各自保留无副作用",
    ),
    "app/agents/rag/cache.py::_pdf_quality_cache": (
        "D",
        "纯文本与元数据哈希的纯函数分析结果缓存，无外部状态依赖，多 worker 各自保留无副作用",
    ),
    "app/agents/rag/web_utils.py::_global_metrics": (
        "D",
        "Web 搜索度量统计单例，按进程汇总计数与延迟，多进程各自保留自身统计",
    ),
    "app/agents/registry.py::_GLOBAL_AGENT_REGISTRY": (
        "D",
        "领域专家智能体全局只读注册表，启动时加载内置智能体，多进程独立保留",
    ),
    "app/agents/registry.py::_REGISTRY_LOCK": (
        "D",
        "智能体注册表互斥锁，多进程各持一份保护自身单例初始化与查找",
    ),
    "app/agents/router/routing.py::_calibrator": (
        "A",
        "仅在 ENABLE_CALIBRATION=true 时生效（默认关闭）；多 worker 下各自累积反馈，并发写校准文件",
    ),
    "app/agents/router/routing.py::_calibrator_lock": (
        "D",
        "保护 _calibrator 的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/agents/shared/cache.py::_router_decision_cache": (
        "B",
        "路由决策缓存 30 分钟，读取了两个可在管理后台修改的配置项，改配置后其他 worker 的缓存不会被清掉",
    ),
    "app/agents/shared/config.py::_config_instance": (
        "D",
        "智能体统一配置单例，仅包含纯内存静态默认配置，各进程可独立保留",
    ),
    "app/agents/verifier/validation/nli.py::load_nli_cross_encoder": (
        "B",
        "NLI 交叉编码器模型单例缓存，模型配置更新时需要跨进程失效或重新加载",
    ),
    "app/agents/verifier/validation/public.py::_cascade_load_attempted": (
        "B",
        "校验级联加载尝试标志，与校验级联缓存联动，热重载时需要重置",
    ),
    "app/agents/verifier/validation/public.py::_validation_cascade": (
        "B",
        "答案校验级联实例缓存，重载配置时需要跨进程失效并重新构建校验器",
    ),
    "app/api/application/lifespan.py::_auto_ingest_thread": (
        "D",
        "自动摄取监视线程只在 STATE_BACKEND=memory（单进程）时由 API 启动；shared 模式下监视器运行在唯一的 ingest-worker 里（阶段 5）",
    ),
    "app/api/application/lifespan.py::_cache_initialized": (
        "D",
        "进程生命周期内缓存服务初始化状态标志，各进程独立维护自身的启停状态",
    ),
    "app/api/dependencies.py::_auto_ingest_stop_event": (
        "D",
        "配合上面的监视线程，只在 memory 模式（单进程）使用",
    ),
    "app/api/dependencies.py::_query_runtime": (
        "D",
        "查询运行时快照，每个进程各一份即可；其中的查询守卫在 STATE_BACKEND=shared 时以 Redis 名额租约跨 worker 共享（ARC-01 阶段 2b）",
    ),
    "app/api/dependencies.py::_runtime_reload_lock": (
        "D",
        "查询运行时热重载线程锁，多进程各持一份保护自身内部运行时替换",
    ),
    "app/api/dependencies.py::auto_ingest_watcher": (
        "D",
        "API 进程里的监视器只在 memory 模式启动；shared 模式由 ingest-worker 自己构造并运行（阶段 5）",
    ),
    "app/api/dependencies.py::prompt_store": (
        "D",
        "基于 SQLite 的提示词模板仓储，本身无内存状态，各进程可保留独立实例",
    ),
    "app/api/routes/operations/metrics_collectors.py::_cache_lock": (
        "D",
        "保护下面依赖探测缓存的进程内锁",
    ),
    "app/api/routes/operations/metrics_collectors.py::_cached": (
        "D",
        "抓取 /metrics 时依赖探测结果的短时缓存（15 秒），每个 worker 各自探测，结果描述的是整个部署（阶段 8）",
    ),
    "app/api/dependencies.py::settings": (
        "B",
        "全局配置对象引用，管理重载配置时需要跨进程同步刷新或重新加载",
    ),
    "app/api/deps/auth.py::auth_service": (
        "D",
        "基于 SQLite 数据库的用户认证服务实例，各进程可独立持有无状态服务对象",
    ),
    "app/api/routes/public/auth.py::oauth_state_store": (
        "D",
        "OAuth state 在 Redis 里；STATE_BACKEND=shared 时 Redis 不可用返回 503，不再退回进程内存（ARC-01 阶段 2f）",
    ),
    "app/api/routes/public/orchestration.py::_pending_subscriptions": (
        "D",
        "每个用户正在等待尚未开始的执行的订阅数，用于每进程的并发上限（ARC-02）；按 worker 计数足以防止一个调用方耗尽一个进程",
    ),
    "app/api/transport/middleware.py::_request_metrics": (
        "D",
        "请求度量环形缓冲区，各进程保留自身请求性能数据供监控采样",
    ),
    "app/api/transport/middleware.py::_request_metrics_lock": (
        "D",
        "请求度量环形缓冲区互斥锁，多进程各持一份保护自身度量数据读写",
    ),
    "app/core/config.py::_PENDING": (
        "D",
        "配置重载临时候选对象，重载完成后立即清空，属于单进程瞬态变量",
    ),
    "app/core/config.py::_RELOAD_LOCK": (
        "D",
        "配置重载互斥锁，保证单个工作进程内热重载配置的原子执行",
    ),
    "app/core/config.py::get_settings": (
        "B",
        "全局配置对象缓存，运行时热重载配置或配置中心推送变更时需要跨进程清理失效",
    ),
    "app/mcp/runtime.py::_lock": (
        "D",
        "工具栈延迟初始化线程互斥锁，多进程各持一份保护自身单例构建",
    ),
    "app/mcp/runtime.py::_stack": (
        "D",
        "工具栈每个进程各一份即可：审批令牌存 app.db（阶段 2c），工具审计写 audit_logs（阶段 2d），不再有只在本进程的数据",
    ),
    "app/orchestration/answer_stream.py::_default_store": (
        "D",
        "每个 worker 各一份：shared 模式下每个脱敏草稿片段同时写入该执行的 Redis 流，SSE 从流里读（ARC-01 阶段 3）",
    ),
    "app/orchestration/answer_stream.py::_default_thought_store": (
        "D",
        "每个 worker 各一份：shared 模式下每个脱敏推理片段同时写入该执行的 Redis 流，SSE 从流里读（ARC-01 阶段 3）",
    ),
    "app/orchestration/execution_events.py::_default_store": (
        "D",
        "每个 worker 各一份：shared 模式下每个阶段事件同时写入该执行的 Redis 流，SSE 从流里读（ARC-01 阶段 3）",
    ),
    "app/orchestration/shared_execution.py::_READER": (
        "D",
        "SSE 读取共享执行流用的异步 Redis 连接器，持有本进程的连接和故障冷却期，每个 worker 各一份",
    ),
    "app/orchestration/shared_execution.py::_WRITER": (
        "D",
        "共享执行流的后台写入线程和队列，写入的数据在 Redis 里；队列本身只缓冲本进程待发送的写入",
    ),
    "app/pipeline/rag_pipeline.py::_ENGINE_CACHE": (
        "D",
        "已编译的 LangGraph 工作流引擎缓存，纯不可变计算图各进程独立持有即可",
    ),
    "app/retrievers/bm25_retriever.py::_load_bm25": (
        "B",
        "全局 BM25 倒排索引缓存；阶段 6：shared 模式下每个请求开始时比对 qm:gen:corpus，落后即清空（摄取、删除、全量重建后 announce）",
    ),
    "app/retrievers/bm25_retriever.py::_load_scoped_bm25": (
        "B",
        "权限分域的 BM25 倒排索引缓存；阶段 6：shared 模式下每个请求开始时比对 qm:gen:corpus，落后即清空",
    ),
    "app/retrievers/hybrid/caching.py::_REDIS": (
        "D",
        "检索缓存的 Redis 连接器，持有本进程的连接池和故障冷却期；连接本身不能跨进程共享，每个 worker 各一份",
    ),
    "app/retrievers/hybrid/caching.py::_RETRIEVAL_CACHE": (
        "B",
        "进程内检索结果缓存，只在 memory 模式使用；shared 模式只用 Redis，键里带语料代号（阶段 6）",
    ),
    "app/retrievers/reranker.py::_load_cross_encoder": (
        "B",
        "重排序 CrossEncoder 模型单例缓存，模型参数变更时需要跨进程失效重建",
    ),
    "app/retrievers/stores/vector.py::_VECTOR_OP_LOCK": (
        "D",
        "向量库本地集合操作互斥锁，多进程各持一份保护底层 Chroma 客户端操作",
    ),
    "app/retrievers/stores/vector.py::_get_vector_store_cached": (
        "B",
        "Chroma 句柄缓存，持有 embedding 函数；阶段 6：shared 模式下每个请求开始时比对 qm:gen:model_settings 和 config，落后即清空",
    ),
    "app/services/auth/redis_rate_limit.py::_rate_limiter": (
        "D",
        "中间件限流计数在 Redis 里；STATE_BACKEND=shared 时 Redis 不可用返回 503，不再按进程计数（ARC-01 阶段 2f）",
    ),
    "app/services/caching/__init__.py::_cache_manager_instance": (
        "B",
        "全局两级缓存管理器单例，包含进程内 L1 内存缓存，跨进程更新时需协调失效",
    ),
    "app/services/context_management.py::_context_service_instance": (
        "A",
        "多轮对话实体追踪与指代消解上下文服务，会话状态保存在内存字典中，多 worker 下状态丢失",
    ),
    "app/services/language/analytics.py::LanguageAnalytics._instance": (
        "D",
        "语言检测统计分析单例，保存在进程内存中的度量指标，各进程可独立保留自身事件流",
    ),
    "app/services/models/runtime.py::_build_chat_model_cached": (
        "B",
        "聊天模型客户端实例缓存，管理员后台更新模型配置时需要跨进程失效清理",
    ),
    "app/services/models/runtime.py::_build_embedding_model_cached": (
        "B",
        "嵌入模型客户端实例缓存，管理员后台更新模型配置时需要跨进程失效清理",
    ),
    "app/services/models/runtime.py::_load_local_embedder": (
        "B",
        "本地嵌入模型权重加载缓存，模型路径或类型变更时需要跨进程失效",
    ),
    "app/services/observability/agent_execution_tracker.py::AgentExecutionTracker._instance": (
        "D",
        "每个 worker 各一份：SSE 需要的归属和状态在 shared 模式下写入 Redis，看板统计写入 SQLite（ARC-01 阶段 3）；含问题原文的完整调试记录按决定只留在本进程，/agent-tracking 只能看到本 worker",
    ),
    "app/services/observability/alerting.py::_LAST_SENT": (
        "A",
        "告警发送冷却时间字典，多 worker 下各持一份会导致告警抑制失效并对渠道重复报警",
    ),
    "app/services/observability/alerting.py::_LOCK": (
        "D",
        "保护 _LAST_SENT 的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/services/observability/log_buffer.py::_BUFFER": (
        "D",
        "内存环形日志记录缓冲区，按进程保留自身的运行时日志记录供控制台查看",
    ),
    "app/services/observability/log_buffer.py::_INSTALLED": (
        "D",
        "日志捕获处理器安装状态标志，属于单进程日志系统初始化标记",
    ),
    "app/services/observability/log_buffer.py::_LOCK": (
        "D",
        "日志缓冲区读写同步互斥锁，多进程各持一份保护自身日志缓冲区",
    ),
    "app/services/observability/log_safety.py::_INSTALLED": (
        "D",
        "日志控制字符转义拦截器安装标记，单进程日志安全防护初始化标志",
    ),
    "app/services/observability/log_safety.py::_URL_REDACTION_INSTALLED": (
        "D",
        "日志 URL 脱敏拦截器安装状态标志，单进程日志系统安全标记",
    ),
    "app/services/performance/monitor.py::_global_monitor": (
        "D",
        "性能监控度量收集器单例，按进程汇总统计指标，多进程各自保留本地度量",
    ),
    "app/services/prompts/report_editor.py::_ai_editor": (
        "D",
        "AI 报告编辑器无状态服务单例，多进程各持一份调用底层模型",
    ),
    "app/services/query/guard.py::_REDIS": (
        "D",
        "查询守卫的 Redis 连接器，持有本进程的连接池和故障冷却期；连接本身不能跨进程共享，每个 worker 各一份",
    ),
    "app/services/query/keyword_match.py::_latin_keyword_pattern": (
        "D",
        "拉丁关键词正则模式纯计算缓存，各进程可独立保留且无副作用",
    ),
    "app/services/retrieval/logger.py::RetrievalLogger._instance": (
        "D",
        "检索日志与性能统计单例，内部维护环形度量日志缓冲区，多进程可各自保留进程内日志",
    ),
    "app/services/runtime/bulkhead.py::_LOCK": (
        "D",
        "保护 _SEMAPHORES 的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/services/runtime/bulkhead.py::_SEMAPHORES": (
        "D",
        "每个 worker 各自保护自己；并发上限会随 worker 数放大，部署时按 worker 数平分配置",
    ),
    "app/services/runtime/file_locks.py::_LOCKS": (
        "D",
        "每个锁文件在本进程内对应一个 FileLock 对象；真正的互斥由操作系统文件锁完成，跨进程天然生效",
    ),
    "app/services/runtime/file_locks.py::_LOCKS_GUARD": (
        "D",
        "保护上面 FileLock 缓存的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/services/runtime/ingest_queue.py::_RQ_CONNECTOR": (
        "D",
        "每个进程一个到 Redis 的连接器（RQ 需要不解码响应），队列本身在 Redis 里，各进程共享",
    ),
    "app/services/runtime/invalidation.py::_CONFIG_HANDLERS": (
        "D",
        "本进程里“配置变了”要做什么（API 与 worker 各自注册 apply_config_reload），无需共享",
    ),
    "app/services/runtime/invalidation.py::_LOCK": (
        "D",
        "保护本进程已应用代号和待发送通知的进程内锁",
    ),
    "app/services/runtime/invalidation.py::_PENDING": (
        "D",
        "Redis 不可用时没能发出的失效通知，本进程下次 catch_up/announce 时重发；丢失只会推迟而不会漏掉",
    ),
    "app/services/runtime/ingest_queue.py::_EXECUTOR": (
        "D",
        "只在 memory 模式（单进程）运行摄取与重建任务；shared 模式任务进 Redis 的 RQ 队列，由唯一的 ingest-worker 执行（阶段 5）",
    ),
    "app/services/runtime/redis_connector.py::_ERRORS": (
        "D",
        "Redis 异常类型元组的惰性缓存，只是类型引用，每个进程解析一次即可",
    ),
    "app/services/runtime/redis_connector.py::_REGISTRY": (
        "D",
        "本进程创建的 Redis 连接器登记表，只供管理员就绪探针报告本进程的连接状态",
    ),
    "app/services/runtime/redis_connector.py::_REGISTRY_LOCK": (
        "D",
        "保护 _REGISTRY 的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/services/runtime/resilience.py::_BREAKERS": (
        "D",
        "每个 worker 各自计数、各自熔断；故障被分散到 N 个进程后，每个进程要各自攒够失败次数才会熔断，保护来得更慢，但不会出错",
    ),
    "app/services/runtime/resilience.py::_BREAKERS_LOCK": (
        "D",
        "保护 _BREAKERS 的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/services/runtime/runtime_ops.py::_LOCK": (
        "D",
        "运维运行时状态同步互斥锁，多进程各持一份保护本地运行时操作",
    ),
    "app/services/runtime/runtime_ops.py::_SERVICE_HEALTH_CACHE": (
        "D",
        "服务健康状态短时缓存，各 worker 定期独立探测和刷新，无需跨进程同步",
    ),
    "app/services/runtime/runtime_ops.py::_SERVICE_HEALTH_LOCK": (
        "D",
        "服务健康检查缓存读取互斥锁，多进程各持一份保护自身缓存",
    ),
    "app/services/runtime/shared_state.py::_CONNECTOR": (
        "D",
        "共享状态用的 Redis 连接器，持有本进程的连接池和故障冷却期；共享的数据在 Redis 里，连接本身每个 worker 各一份",
    ),
    "app/services/security/admin_token_tracker.py::_global_tracker": (
        "D",
        "管理员一次性令牌的使用记录存在 app.db，用原子 UPSERT 认领，所有 worker 共享（ARC-01 阶段 2e）",
    ),
    "app/services/security/injection_defense.py::_GLOBAL_DETECTOR": (
        "D",
        "提示词注入防御检测器无状态单例，纯规则与正则匹配，各进程可保留独立实例",
    ),
    "app/services/security/outbound_redaction.py::_custom_patterns": (
        "B",
        "出站脱敏自定义正则缓存，配置更新时需要跨进程失效清理缓存",
    ),
    "app/services/sessions/history.py::_LOCK_REGISTRY": (
        "D",
        "进程内会话锁，阶段 4 后只是优化：sqlite 后端的每次改动都在 BEGIN IMMEDIATE 事务里跨进程串行，file 后端在 STATE_BACKEND=shared 下拒绝启动",
    ),
    "app/services/sessions/history.py::_LOCK_REGISTRY_GUARD": (
        "D",
        "保护会话锁注册表 _LOCK_REGISTRY 的进程内互斥锁，本身不需要跨进程共享",
    ),
    "app/services/sessions/metadata_db.py::_metadata_db_instances": (
        "D",
        "每个元数据库文件一个服务对象；阶段 6 起不再有进程内缓存，读写都直接访问 SQLite，更新是一个 BEGIN IMMEDIATE 事务",
    ),
    "app/services/sessions/service.py::_memory_service_instances": (
        "D",
        "仅 SESSION_METADATA_BACKEND=memory 使用；STATE_BACKEND=shared 拒绝该后端（阶段 4），所以只在单进程部署里存在",
    ),
    "app/services/tables/store.py::_GLOBAL_LOCK": (
        "D",
        "表格存储单例初始化互斥锁，多进程各持一份保护自身单例构建",
    ),
    "app/services/tables/store.py::_GLOBAL_TABLE_STORE": (
        "B",
        "表格存储全局服务单例，包含进程内 TableEngine LRU 缓存，更新时需要跨进程失效",
    ),
    "app/services/web_activity/alerts.py::_global_alert_system": (
        "D",
        "Web 活动告警系统单例，维护本地规则与告警触发历史，各进程可独立保留",
    ),
    "app/services/web_activity/data_manager.py::_global_data_manager": (
        "D",
        "Web 活动数据备份归档管理器单例，无内存状态，各进程可保留独立实例",
    ),
    "app/services/web_activity/logger.py::_global_activity_analyzer": (
        "D",
        "Web 搜索活动日志分析器单例，按需读取磁盘日志文件进行分析，各进程可保留独立实例",
    ),
    "app/services/web_activity/logger.py::_global_activity_logger": (
        "D",
        "Web 搜索活动日志记录器单例，直接追加写入磁盘 jsonl 文件，各进程可保留独立实例",
    ),
    "app/tools/ai/code_sandbox.py::AI_MATH_TOOL_DEFINITION": (
        "D",
        "AI 代码沙箱工具静态定义常量对象，不可变元数据，多进程可各自持有独立实例",
    ),
    "app/tools/cyber/cve_tools.py::ATTACK_TOOL_DEFINITION": (
        "D",
        "网络攻击模式工具静态定义常量对象，不可变元数据，多进程可各自持有独立实例",
    ),
    "app/tools/cyber/cve_tools.py::CVE_TOOL_DEFINITION": (
        "D",
        "CVE 漏洞查询工具静态定义常量对象，不可变元数据，多进程可各自持有独立实例",
    ),
    "app/tools/registry.py::_GLOBAL_REGISTRY": (
        "D",
        "工具提供者全局注册表，启动时加载内置提供者，各进程可独立保留只读注册表",
    ),
    "app/tools/registry.py::_REGISTRY_LOCK": (
        "D",
        "工具注册表互斥锁，多进程各持一份保护单进程内的工具初始化与发现",
    ),
    "app/tools/web/factory.py::_PROVIDER_CACHE": (
        "B",
        "Web 搜索提供者实例缓存，配置热重载时需要跨进程失效重建",
    ),
    "app/tools/web/factory.py::_PROVIDER_LOCK": (
        "D",
        "Web 搜索提供者缓存互斥锁，多进程各持一份保护自身缓存构建",
    ),
    "app/tools/web/providers/duckduckgo.py::_CLIENT_LOCK": (
        "D",
        "DDGS 客户端并发实例化互斥锁，多进程各持一份保护自身客户端构造",
    ),
}
