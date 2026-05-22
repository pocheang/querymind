# PDF模块P3改进设计文档

**日期**: 2026-05-15  
**版本**: 1.0  
**状态**: 设计阶段

---

## 1. 概述

### 1.1 目标
为PDF处理模块实施所有P3（低优先级）改进，提升代码质量、性能和可维护性。

### 1.2 背景
PDF模块已完成P0-P2问题修复（10/10），当前状态健康。P3改进将进一步提升：
- 测试覆盖率和代码可靠性
- 性能和成本效率
- 可观测性和监控能力

### 1.3 实施方案
采用**方案A：按优先级顺序实施**
- 优势：测试优先，降低风险，阶段性成果
- 时间线：4周
- 风险：最低

---

## 2. 整体架构

### 2.1 新增文件结构

```
tests/
├── unit/
│   ├── test_pdf_loader.py           # PDF加载器单元测试
│   ├── test_chart_extractor.py      # 图表提取单元测试
│   ├── test_performance_cache.py    # 缓存系统单元测试
│   └── test_pdf_utils.py            # 工具函数单元测试
├── performance/
│   ├── benchmark_pdf_processing.py  # 性能基准测试
│   └── benchmark_results.json       # 基准测试结果
└── integration/
    └── test_error_scenarios.py      # 错误场景集成测试

app/ingestion/utils/
├── batch_chart_extractor.py         # 批量图表提取
├── streaming_pdf_loader.py          # 流式PDF处理
└── monitoring.py                    # 监控指标收集

docs/
├── PDF_TESTING_GUIDE.md             # 测试指南
└── PDF_PERFORMANCE_TUNING.md        # 性能调优指南
```

### 2.2 实施阶段

**第1周：测试基础设施**
- 单元测试框架和核心函数测试
- 性能基准测试系统

**第2周：错误场景测试 + 批量优化**
- 边界条件和错误场景测试
- 批量图表提取（降低API成本）

**第3周：流式处理 + 缓存优化**
- 大PDF流式处理（降低内存峰值）
- 智能缓存失效（TTL + 版本控制）

**第4周：监控和文档**
- 监控指标收集
- 文档完善和最佳实践

---

## 3. 第1周：测试基础设施

### 3.1 单元测试框架

#### 3.1.1 测试覆盖目标
- **核心加载器**：`load_pdf_enhanced`, `load_pdf_advanced`, `load_pdf_text`
- **图表提取**：`extract_chart_data_with_vision`, `detect_chart_in_image`
- **缓存系统**：`PDFProcessingCache`的所有方法
- **工具函数**：`compute_file_hash`, `compute_config_hash`, 图片缩放等

#### 3.1.2 测试策略
- 使用pytest作为测试框架
- Mock外部API调用（OpenAI/Anthropic）
- 使用fixture提供测试PDF文件
- 参数化测试覆盖多种配置组合

#### 3.1.3 关键测试用例

**tests/unit/test_performance_cache.py**
```python
def test_cache_with_different_configs():
    """验证不同配置使用不同缓存键"""
    
def test_cache_atomic_write():
    """验证并发写入安全性"""
    
def test_cache_hit_and_miss():
    """验证缓存命中和未命中逻辑"""
    
def test_cache_clear_operations():
    """验证缓存清理功能"""
```

**tests/unit/test_chart_extractor.py**
```python
def test_image_resize_large_file():
    """验证5MB限制和自动缩放"""
    
def test_chart_detection_heuristics():
    """验证图表检测逻辑"""
    
def test_vision_api_error_handling():
    """验证API错误处理"""
    
def test_json_extraction_strategies():
    """验证多策略JSON解析"""
```

**tests/unit/test_pdf_loader.py**
```python
def test_loader_with_various_configs():
    """验证配置参数正确传递"""
    
def test_fallback_chain_logic():
    """验证降级逻辑"""
    
def test_resource_cleanup():
    """验证资源正确释放"""
```

### 3.2 性能基准测试系统

#### 3.2.1 基准测试指标
- **处理时间**：按模式（pypdf, docling_enhanced, docling_advanced）
- **内存峰值**：使用memory_profiler
- **API调用次数**：图表提取
- **缓存命中率**：缓存效果

#### 3.2.2 测试数据集
- 小文件（<5页）
- 中等文件（10-20页）
- 大文件（50+页）
- 包含图表的文件

#### 3.2.3 输出格式
```json
{
  "timestamp": "2026-05-15T10:00:00",
  "benchmarks": {
    "pypdf_small": {
      "time_seconds": 2.3,
      "memory_mb": 45,
      "pages": 3
    },
    "docling_enhanced_medium": {
      "time_seconds": 38.5,
      "memory_mb": 320,
      "pages": 15
    },
    "chart_extraction": {
      "api_calls": 5,
      "time_seconds": 12.3,
      "estimated_cost_usd": 0.05
    }
  }
}
```

#### 3.2.4 实现
```python
# tests/performance/benchmark_pdf_processing.py

import time
import psutil
from pathlib import Path
from app.ingestion.loaders import load_pdf_enhanced

def benchmark_loader(pdf_path: Path, mode: str) -> dict:
    """基准测试单个加载器"""
    process = psutil.Process()
    
    # 记录初始内存
    mem_before = process.memory_info().rss / 1024 / 1024
    
    # 执行加载
    start = time.time()
    docs = load_pdf_enhanced(pdf_path)
    duration = time.time() - start
    
    # 记录峰值内存
    mem_after = process.memory_info().rss / 1024 / 1024
    mem_peak = mem_after - mem_before
    
    return {
        "time_seconds": duration,
        "memory_mb": mem_peak,
        "num_docs": len(docs)
    }
```

---

## 4. 第2周：错误场景测试 + 批量优化

### 4.1 错误场景测试

#### 4.1.1 测试用例
```python
# tests/integration/test_error_scenarios.py

def test_corrupted_pdf_handling():
    """测试损坏的PDF文件处理"""
    
def test_missing_api_key():
    """测试API密钥缺失场景"""
    
def test_network_timeout():
    """测试网络超时处理"""
    
def test_invalid_image_format():
    """测试无效图片格式"""
    
def test_concurrent_cache_access():
    """测试并发缓存访问"""
    
def test_disk_full_scenario():
    """测试磁盘空间不足"""
    
def test_memory_limit_exceeded():
    """测试内存限制超出"""
```

### 4.2 批量图表提取

#### 4.2.1 设计目标
- 减少API调用延迟（通过并发）
- 保持成本不变（调用次数相同）
- 提升用户体验（更快完成）

#### 4.2.2 实现
```python
# app/ingestion/utils/batch_chart_extractor.py

import asyncio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class BatchChartExtractor:
    """批量提取图表，使用异步并发"""
    
    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size
    
    async def extract_charts_batch(
        self,
        images: List[bytes],
        model: str,
        api_key: str
    ) -> List[Dict]:
        """
        批量提取图表数据
        
        Args:
            images: 图片字节列表
            model: 模型名称
            api_key: API密钥
            
        Returns:
            图表数据列表
        """
        results = []
        
        # 分批处理
        for i in range(0, len(images), self.batch_size):
            batch = images[i:i + self.batch_size]
            
            # 并发调用API
            tasks = [
                self._extract_single_async(img, model, api_key)
                for img in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
        return results
    
    async def _extract_single_async(
        self,
        image_bytes: bytes,
        model: str,
        api_key: str
    ) -> Dict:
        """异步提取单个图表"""
        # 使用异步HTTP客户端
        # 实现略
        pass
```

#### 4.2.3 集成到现有代码
```python
# 修改 app/ingestion/loaders/pdf_chart_loader.py

def extract_charts_from_pdf(
    path: Path,
    use_vision: bool = True,
    vision_model: str = "gpt-4-vision",
    use_batch: bool = True  # 新参数
) -> List[Document]:
    """提取图表，支持批量模式"""
    
    # 收集所有图片
    all_images = []
    for page in reader.pages:
        images = list(page.images or [])
        for img_obj in images:
            img_bytes = getattr(img_obj, "data", None)
            if img_bytes and detect_chart_in_image(img_bytes).get("is_chart"):
                all_images.append(img_bytes)
    
    # 批量提取
    if use_batch and len(all_images) > 1:
        extractor = BatchChartExtractor()
        chart_data_list = asyncio.run(
            extractor.extract_charts_batch(all_images, vision_model, api_key)
        )
    else:
        # 单个提取（原有逻辑）
        chart_data_list = [
            extract_chart_data_with_vision(img, vision_model, api_key)
            for img in all_images
        ]
    
    # 转换为Document
    # ...
```

#### 4.2.4 预期效果
- API调用总时间减少40%（5个图表：从15秒降到9秒）
- 成本不变（调用次数相同）
- 用户体验提升

---

## 5. 第3周：流式处理 + 缓存优化

### 5.1 流式PDF处理

#### 5.1.1 设计目标
- 降低内存峰值70%（对于100页PDF）
- 支持超大文件（1000+页）
- 提前开始处理结果

#### 5.1.2 实现
```python
# app/ingestion/utils/streaming_pdf_loader.py

from typing import Iterator
from pathlib import Path
from langchain_core.documents import Document

def load_pdf_streaming(
    path: Path,
    chunk_pages: int = 10,
    mode: str = "docling_enhanced"
) -> Iterator[Document]:
    """
    流式处理PDF，分块加载和处理
    
    Args:
        path: PDF文件路径
        chunk_pages: 每次处理的页数
        mode: 处理模式
        
    Yields:
        Document对象
    """
    from docling.document_converter import DocumentConverter
    
    converter = DocumentConverter()
    result = converter.convert(str(path))
    
    # 分块处理页面
    pages = list(result.document.pages)
    for i in range(0, len(pages), chunk_pages):
        chunk = pages[i:i + chunk_pages]
        
        # 处理当前块
        for page_idx, page in enumerate(chunk, start=i+1):
            page_markdown = page.export_to_markdown()
            
            if page_markdown and page_markdown.strip():
                # 立即yield，不等待所有页面
                yield Document(
                    page_content=page_markdown,
                    metadata={
                        "source": str(path),
                        "page": page_idx,
                        "total_pages": len(pages)
                    }
                )
```

#### 5.1.3 使用示例
```python
# 流式处理大PDF
for doc in load_pdf_streaming(large_pdf_path):
    # 立即处理每个文档
    process_document(doc)
    # 内存只保留当前块
```

### 5.2 智能缓存失效

#### 5.2.1 设计目标
- 自动清理过期缓存
- 支持TTL配置
- 避免缓存无限增长

#### 5.2.2 实现
```python
# 增强 app/ingestion/utils/performance.py

import time
from datetime import datetime

class PDFProcessingCache:
    """缓存系统，支持TTL"""
    
    def __init__(
        self,
        cache_dir: Path = Path("./data/cache/pdf_processing"),
        ttl_days: int = 30
    ):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_days * 24 * 3600
    
    def is_cache_valid(self, cache_path: Path) -> bool:
        """检查缓存是否有效（未过期）"""
        if not cache_path.exists():
            return False
        
        # 检查年龄
        age = time.time() - cache_path.stat().st_mtime
        return age < self.ttl_seconds
    
    def get(
        self,
        file_path: Path,
        operation: str,
        config: Optional[Dict] = None
    ) -> Optional[Any]:
        """获取缓存，检查TTL"""
        cache_path = self.get_cache_path(file_path, operation, config)
        
        # 检查是否过期
        if not self.is_cache_valid(cache_path):
            if cache_path.exists():
                logger.info(f"Cache expired for {file_path.name}, removing")
                cache_path.unlink()
            return None
        
        # 读取缓存
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Cache hit for {file_path.name} - {operation}")
                return data
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
            return None
    
    def cleanup_expired(self) -> int:
        """清理所有过期缓存"""
        cleaned = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            if not self.is_cache_valid(cache_file):
                try:
                    cache_file.unlink()
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {cache_file}: {e}")
        
        if cleaned > 0:
            logger.info(f"Cleaned {cleaned} expired cache entries")
        
        return cleaned
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        total_files = 0
        total_size = 0
        expired_files = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            total_files += 1
            total_size += cache_file.stat().st_size
            
            if not self.is_cache_valid(cache_file):
                expired_files += 1
        
        return {
            "total_files": total_files,
            "total_size_mb": total_size / 1024 / 1024,
            "expired_files": expired_files,
            "valid_files": total_files - expired_files
        }
```

#### 5.2.3 配置
```bash
# .env
PDF_CACHE_TTL_DAYS=30           # 缓存有效期（天）
PDF_STREAMING_CHUNK_SIZE=10     # 流式处理块大小
PDF_BATCH_CHART_SIZE=5          # 批量图表提取大小
```

---

## 6. 第4周：监控和文档

### 6.1 监控指标收集

#### 6.1.1 设计目标
- 收集关键性能指标
- 支持趋势分析
- 帮助识别问题

#### 6.1.2 实现
```python
# app/ingestion/utils/monitoring.py

import json
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta

class PDFProcessingMetrics:
    """PDF处理指标收集"""
    
    def __init__(self, metrics_file: Path = Path("./data/metrics/pdf_processing.jsonl")):
        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
    
    def record_processing(
        self,
        file_path: Path,
        mode: str,
        duration: float,
        memory_mb: float,
        cache_hit: bool,
        api_calls: int = 0,
        num_pages: int = 0,
        error: Optional[str] = None
    ):
        """记录单次处理指标"""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "file_name": file_path.name,
            "file_size_mb": file_path.stat().st_size / 1024 / 1024,
            "mode": mode,
            "duration_seconds": duration,
            "memory_mb": memory_mb,
            "cache_hit": cache_hit,
            "api_calls": api_calls,
            "num_pages": num_pages,
            "error": error
        }
        
        # 追加到JSONL文件
        with open(self.metrics_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metric, ensure_ascii=False) + '\n')
    
    def get_summary(self, days: int = 7) -> Dict:
        """获取最近N天的统计摘要"""
        if not self.metrics_file.exists():
            return {}
        
        cutoff = datetime.now() - timedelta(days=days)
        metrics = []
        
        # 读取指标
        with open(self.metrics_file, 'r', encoding='utf-8') as f:
            for line in f:
                metric = json.loads(line)
                timestamp = datetime.fromisoformat(metric["timestamp"])
                if timestamp >= cutoff:
                    metrics.append(metric)
        
        if not metrics:
            return {}
        
        # 计算统计
        total = len(metrics)
        cache_hits = sum(1 for m in metrics if m["cache_hit"])
        total_api_calls = sum(m["api_calls"] for m in metrics)
        total_duration = sum(m["duration_seconds"] for m in metrics)
        errors = sum(1 for m in metrics if m.get("error"))
        
        return {
            "period_days": days,
            "total_processed": total,
            "avg_time_seconds": total_duration / total if total > 0 else 0,
            "cache_hit_rate": cache_hits / total if total > 0 else 0,
            "total_api_calls": total_api_calls,
            "estimated_cost_usd": total_api_calls * 0.01,  # 估算
            "error_rate": errors / total if total > 0 else 0
        }
```

#### 6.1.3 使用示例
```python
# 在加载器中集成监控
from app.ingestion.utils.monitoring import PDFProcessingMetrics

metrics = PDFProcessingMetrics()

start = time.time()
try:
    docs = load_pdf_enhanced(pdf_path)
    duration = time.time() - start
    
    metrics.record_processing(
        file_path=pdf_path,
        mode="docling_enhanced",
        duration=duration,
        memory_mb=get_memory_usage(),
        cache_hit=False,
        num_pages=len(docs)
    )
except Exception as e:
    duration = time.time() - start
    metrics.record_processing(
        file_path=pdf_path,
        mode="docling_enhanced",
        duration=duration,
        memory_mb=0,
        cache_hit=False,
        error=str(e)
    )
    raise
```

### 6.2 文档更新

#### 6.2.1 新增文档

**docs/PDF_TESTING_GUIDE.md**
- 如何运行单元测试
- 如何运行性能基准测试
- 如何添加新测试
- 测试最佳实践

**docs/PDF_PERFORMANCE_TUNING.md**
- 性能调优指南
- 配置参数说明
- 批量处理建议
- 流式处理使用场景
- 缓存策略

#### 6.2.2 更新现有文档

**docs/API_SETTINGS_GUIDE.md**
添加新配置项：
```bash
# P3改进新增配置
PDF_CACHE_TTL_DAYS=30           # 缓存有效期
PDF_STREAMING_CHUNK_SIZE=10     # 流式处理块大小
PDF_BATCH_CHART_SIZE=5          # 批量图表提取大小
PDF_ENABLE_METRICS=true         # 启用指标收集
```

---

## 7. 测试策略

### 7.1 单元测试
- 覆盖率目标：80%+
- 使用pytest + pytest-cov
- Mock外部依赖
- 快速执行（<30秒）

### 7.2 集成测试
- 测试真实场景
- 使用测试PDF文件
- 验证端到端流程

### 7.3 性能测试
- 建立性能基线
- 回归测试
- 定期运行（每周）

---

## 8. 风险和缓解

### 8.1 风险

**R1: 测试覆盖不完整**
- 缓解：优先测试核心路径，逐步扩展

**R2: 批量提取增加复杂度**
- 缓解：保留单个提取作为fallback

**R3: 流式处理兼容性**
- 缓解：提供传统加载方式作为选项

**R4: 监控开销**
- 缓解：使用异步写入，最小化性能影响

### 8.2 回滚计划
- 所有新功能都有开关（配置项）
- 可以快速禁用新功能
- 保留原有实现作为fallback

---

## 9. 成功指标

### 9.1 测试指标
- 单元测试覆盖率 ≥ 80%
- 所有测试通过
- 性能基准建立

### 9.2 性能指标
- 批量提取：API调用时间减少40%
- 流式处理：内存峰值降低70%（大文件）
- 缓存：自动清理过期条目

### 9.3 质量指标
- 无新增P0/P1问题
- 代码审查通过
- 文档完整

---

## 10. 时间线

| 周 | 任务 | 交付物 |
|----|------|--------|
| 1 | 测试基础设施 | 单元测试套件 + 性能基准 |
| 2 | 错误测试 + 批量优化 | 集成测试 + 批量提取器 |
| 3 | 流式处理 + 缓存优化 | 流式加载器 + TTL缓存 |
| 4 | 监控和文档 | 指标系统 + 完整文档 |

---

## 11. 附录

### 11.1 依赖
- pytest >= 7.0
- pytest-cov
- pytest-asyncio
- memory_profiler
- psutil

### 11.2 配置示例
```bash
# .env 完整配置
PDF_LOADER_MODE=docling_enhanced
PDF_ENABLE_CACHING=true
PDF_CACHE_TTL_DAYS=30
PDF_STREAMING_CHUNK_SIZE=10
PDF_BATCH_CHART_SIZE=5
PDF_ENABLE_METRICS=true
PDF_PARALLEL_WORKERS=4
```

### 11.3 参考文档
- 内部 PDF 修复记录见 `internal_docs/docs_archive/PDF_FIXES_SUMMARY.md`
- 内部 PDF 健康检查见 `internal_docs/docs_archive/PDF_HEALTH_CHECK.md`
- 内部 PDF 问题列表见 `internal_docs/docs_archive/PDF_ISSUES_AND_FIXES.md`
