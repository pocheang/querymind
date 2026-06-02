# 修改计划 - 完成待办工具任务

**变更ID**: CHANGE-2026-06-02-003  
**计划时间**: 2026-06-02 19:00:00  
**计划人**: pocheang & Claude  
**类型**: enhancement | bugfix  
**优先级**: Medium  
**预计工时**: 2-3小时

---

## 📋 背景和目标

### 问题描述
通过代码扫描发现3个未完成的TODO任务：

1. **`scripts/classify_documents.py:184`** - 文档移动逻辑未实现
2. **`scripts/classify_documents.py:197`** - 数据库更新逻辑未实现  
3. **`app/api/routes/evaluation.py:69`** - Retriever实例化未实现

这些TODO标记存在已久，影响了以下功能：
- 文档分类脚本无法实际移动文件
- 文档元数据无法更新到数据库
- 评估API端点无法独立运行

### 目标
完成所有3个TODO任务，使相关功能完整可用。

### 影响范围
- **文件**: 2个 (`scripts/classify_documents.py`, `app/api/routes/evaluation.py`)
- **功能**: 文档分类工具、评估API
- **用户影响**: 提升工具可用性，支持自动化文档管理

---

## 🎯 实施方案

### 任务1: 实现文档移动逻辑

**文件**: `scripts/classify_documents.py:184`

**当前状态**:
```python
def organize_documents_by_category(data_dir: Path = None, dry_run: bool = True):
    # ... 分类逻辑 ...
    if not dry_run:
        print("\n开始组织文档...")
        # TODO: 实现文档移动逻辑
        print("✅ 文档组织完成")
```

**实施方案**:
```python
if not dry_run:
    print("\n开始组织文档...")
    moved_count = 0
    failed_count = 0
    
    for file_path, category in classifications.items():
        try:
            source = data_dir / file_path
            target_dir = data_dir / "classified" / category
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name
            
            # 检查目标文件是否已存在
            if target.exists():
                print(f"⚠️  跳过（已存在）: {file_path}")
                continue
            
            # 移动文件
            import shutil
            shutil.move(str(source), str(target))
            moved_count += 1
            print(f"✅ 已移动: {file_path} -> {category}/")
            
        except Exception as e:
            failed_count += 1
            print(f"❌ 移动失败: {file_path} - {e}")
    
    print(f"\n移动完成: 成功 {moved_count}, 失败 {failed_count}")
```

**风险评估**:
- ⚠️ **数据丢失风险**: 文件移动可能失败
- 🛡️ **缓解措施**: 
  - 默认dry_run=True，需要--execute才执行
  - 移动前检查目标是否存在
  - 使用try-except捕获错误
  - 提供详细日志

---

### 任务2: 实现数据库更新逻辑

**文件**: `scripts/classify_documents.py:197`

**当前状态**:
```python
def update_document_metadata(classifications: dict):
    try:
        # TODO: 实现数据库更新逻辑
        for file_path, category in classifications.items():
            print(f"更新: {file_path} -> {category}")
```

**实施方案**:

需要先分析项目的数据库结构：
- 检查是否有文档表
- 确定元数据存储位置（SQLite/JSON/其他）
- 设计更新逻辑

**方案A**: 使用现有的文档管理系统
```python
from app.db.session import get_session
from app.db.models import Document

def update_document_metadata(classifications: dict):
    print("\n" + "=" * 60)
    print("更新文档元数据")
    print("=" * 60)
    
    try:
        updated_count = 0
        failed_count = 0
        
        with get_session() as session:
            for file_path, category in classifications.items():
                try:
                    # 查找文档记录
                    doc = session.query(Document).filter(
                        Document.source.like(f"%{file_path}")
                    ).first()
                    
                    if doc:
                        # 更新元数据
                        doc.metadata = doc.metadata or {}
                        doc.metadata["category"] = category
                        doc.metadata["classified_at"] = datetime.now().isoformat()
                        session.commit()
                        updated_count += 1
                        print(f"✅ 更新: {file_path} -> {category}")
                    else:
                        print(f"⚠️  未找到记录: {file_path}")
                        
                except Exception as e:
                    failed_count += 1
                    print(f"❌ 更新失败: {file_path} - {e}")
                    session.rollback()
        
        print(f"\n更新完成: 成功 {updated_count}, 失败 {failed_count}")
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
```

**方案B**: 如果没有数据库，使用JSON文件存储
```python
import json
from datetime import datetime

def update_document_metadata(classifications: dict):
    metadata_file = Path("data/document_metadata.json")
    
    # 读取现有元数据
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    else:
        metadata = {}
    
    # 更新分类信息
    for file_path, category in classifications.items():
        metadata[file_path] = {
            "category": category,
            "classified_at": datetime.now().isoformat(),
            "auto_classified": True
        }
    
    # 保存更新后的元数据
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 元数据已保存到: {metadata_file}")
```

**决策**: 先检查项目数据库结构，选择合适方案

---

### 任务3: 实现Retriever实例化

**文件**: `app/api/routes/evaluation.py:69`

**当前状态**:
```python
def get_retriever(system_name: str):
    # TODO: Implement actual retriever instantiation
    raise not_implemented(
        f"Retriever instantiation not yet implemented. "
        f"Please use the evaluation module directly for now."
    )
```

**实施方案**:
```python
from fastapi import Depends
from app.retrievers.hybrid_retriever import HybridRetriever
from app.retrievers.vector_retriever import VectorRetriever
from app.api.utils.dependencies import get_vectorstore, get_corpus_store

def get_retriever(
    system_name: str,
    vectorstore = Depends(get_vectorstore),
    corpus_store = Depends(get_corpus_store)
):
    """Get retriever instance by system name."""
    
    if system_name == "vector_only":
        # 纯向量检索
        return VectorRetriever(
            vectorstore=vectorstore,
            top_k=10
        )
    
    elif system_name == "hybrid":
        # 混合检索（向量 + BM25）
        return HybridRetriever(
            vectorstore=vectorstore,
            corpus_store=corpus_store,
            vector_top_k=10,
            bm25_top_k=10,
            enable_rerank=False
        )
    
    elif system_name == "rerank":
        # 混合检索 + 重排序
        return HybridRetriever(
            vectorstore=vectorstore,
            corpus_store=corpus_store,
            vector_top_k=20,
            bm25_top_k=20,
            enable_rerank=True,
            rerank_top_k=10
        )
    
    else:
        raise bad_request(
            f"Unknown system: {system_name}. "
            f"Available systems: vector_only, hybrid, rerank"
        )
```

**依赖注入调整**:
需要将`get_retriever`作为依赖注入到路由中：

```python
@router.post("/run", response_model=RunEvaluationResponse)
async def run_evaluation(
    request: RunEvaluationRequest,
    vectorstore = Depends(get_vectorstore),
    corpus_store = Depends(get_corpus_store)
):
    # 获取retriever
    retriever = get_retriever(request.system, vectorstore, corpus_store)
    # ... 其余逻辑 ...
```

---

## 🧪 测试计划

### 测试1: 文档移动功能
```bash
# 准备测试数据
mkdir -p data/test_classify
cp data/docs/sample.pdf data/test_classify/

# 预览模式（不实际移动）
conda activate rag-local
python scripts/classify_documents.py --data-dir data/test_classify

# 实际执行
python scripts/classify_documents.py --data-dir data/test_classify --execute

# 验证结果
ls -R data/test_classify/classified/
```

**预期结果**:
- 文件按分类移动到对应目录
- 日志显示成功/失败统计
- 原目录文件已移除

### 测试2: 数据库更新功能
```bash
# 执行分类和更新
python scripts/classify_documents.py --execute --update-db

# 验证元数据（方案A）
python -c "from app.db.session import get_session; from app.db.models import Document; \
           with get_session() as s: print([d.metadata for d in s.query(Document).all()])"

# 验证元数据（方案B）
cat data/document_metadata.json
```

**预期结果**:
- 文档记录包含category字段
- classified_at时间戳正确
- 无数据库错误

### 测试3: 评估API功能
```bash
# 启动后端
conda activate rag-local
uvicorn app.api.main:app --reload

# 测试API端点
curl http://localhost:8000/api/evaluation/systems

# 运行评估
curl -X POST http://localhost:8000/api/evaluation/run \
  -H "Content-Type: application/json" \
  -d '{"system": "hybrid", "query_file": "data/evaluation/demo_queries.json"}'

# 比较系统
curl -X POST http://localhost:8000/api/evaluation/compare \
  -H "Content-Type: application/json" \
  -d '{"systems": ["vector_only", "hybrid", "rerank"]}'
```

**预期结果**:
- API返回200状态码
- 返回有效的评估指标
- 结果保存到data/evaluation/results/

---

## 📊 验收标准

- [ ] 任务1: 文档移动逻辑完整实现
  - [ ] 支持dry_run预览模式
  - [ ] 处理文件已存在情况
  - [ ] 错误处理和日志完善
  - [ ] 测试通过

- [ ] 任务2: 数据库更新逻辑完整实现
  - [ ] 确定数据存储方案
  - [ ] 实现元数据更新
  - [ ] 支持批量更新
  - [ ] 测试通过

- [ ] 任务3: Retriever实例化完整实现
  - [ ] 支持3种系统类型
  - [ ] 依赖注入正确
  - [ ] API端点可用
  - [ ] 测试通过

- [ ] 所有TODO标记已移除
- [ ] 代码审查通过
- [ ] 文档更新完成

---

## 🚨 风险评估

### 风险1: 文件移动可能导致数据丢失
**可能性**: Medium  
**影响**: High  
**缓解措施**:
- 默认dry_run模式
- 移动前备份重要文件
- 详细的操作日志
- 提供回滚脚本

### 风险2: 数据库结构不明确
**可能性**: Medium  
**影响**: Medium  
**缓解措施**:
- 先调研现有数据库设计
- 提供多种实现方案
- 如无数据库，使用JSON替代

### 风险3: 评估API依赖注入复杂
**可能性**: Low  
**影响**: Medium  
**缓解措施**:
- 参考现有路由的依赖注入模式
- 充分测试所有系统类型
- 提供降级方案

---

## 📝 实施步骤

### 步骤1: 代码分析和方案确认（30分钟）
1. [ ] 检查项目数据库结构
2. [ ] 确认文档存储位置
3. [ ] 审查现有Retriever实现
4. [ ] 确定最终技术方案

### 步骤2: 实现任务1 - 文档移动（45分钟）
1. [ ] 实现文件移动逻辑
2. [ ] 添加错误处理
3. [ ] 编写测试脚本
4. [ ] 测试验证

### 步骤3: 实现任务2 - 数据库更新（45分钟）
1. [ ] 根据方案实现更新逻辑
2. [ ] 处理边界情况
3. [ ] 编写测试脚本
4. [ ] 测试验证

### 步骤4: 实现任务3 - Retriever实例化（30分钟）
1. [ ] 实现get_retriever函数
2. [ ] 调整路由依赖注入
3. [ ] 更新API文档
4. [ ] 测试验证

### 步骤5: 集成测试和文档（30分钟）
1. [ ] 端到端测试
2. [ ] 移除所有TODO标记
3. [ ] 更新相关文档
4. [ ] 代码审查

**总计**: ~3小时

---

## 📚 相关文档

- [代码变更管理制度](../../docs/CODE_CHANGE_POLICY.md)
- [快速参考指南](../.claude/QUICK_REFERENCE.md)
- [v0.4.3稳定性修复](v0.4.3-stability-fixes.md)

---

## 🔄 审批流程

- [ ] 技术方案审批: pocheang
- [ ] 风险评估确认: pocheang
- [ ] 开始实施授权: pocheang

---

**计划状态**: 📝 待审批  
**计划创建时间**: 2026-06-02 19:00:00  
**下一步**: 等待用户审批后开始实施
