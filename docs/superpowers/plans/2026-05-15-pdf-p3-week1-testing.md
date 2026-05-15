# PDF P3改进 - 第1周：测试基础设施

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立PDF模块的测试基础设施，包括单元测试框架和性能基准测试系统

**Architecture:** 使用pytest作为测试框架，创建unit/performance/integration测试目录结构。Mock外部API调用，使用fixture提供测试数据。性能基准测试使用psutil监控内存，输出JSON格式结果。

**Tech Stack:** pytest, pytest-cov, pytest-mock, psutil, memory_profiler

---

## 文件结构

**新增文件:**
- `tests/unit/test_performance_cache.py` - 缓存系统单元测试
- `tests/unit/test_chart_extractor.py` - 图表提取单元测试  
- `tests/unit/test_pdf_utils.py` - 工具函数单元测试
- `tests/performance/benchmark_pdf_processing.py` - 性能基准测试
- `tests/conftest.py` - pytest配置和fixtures（如果不存在则创建）

**修改文件:**
- `tests/conftest.py` - 添加PDF测试fixtures

---

### Task 1: 缓存系统单元测试

**Files:**
- Create: `tests/unit/test_performance_cache.py`
- Test: `app/ingestion/utils/performance.py`

- [ ] **Step 1: 创建测试文件和基础结构**

```python
"""Unit tests for PDF processing cache system."""

import pytest
import json
import time
from pathlib import Path
from app.ingestion.utils.performance import (
    PDFProcessingCache,
    compute_file_hash,
    compute_config_hash
)


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest content")
    return pdf_path


@pytest.fixture
def cache(temp_cache_dir):
    """Provide a PDFProcessingCache instance."""
    return PDFProcessingCache(cache_dir=temp_cache_dir)
```

- [ ] **Step 2: 编写配置哈希测试**

```python
def test_compute_config_hash_consistent():
    """Test that same config produces same hash."""
    config1 = {"enable_cleaning": True, "mode": "enhanced"}
    config2 = {"mode": "enhanced", "enable_cleaning": True}
    
    hash1 = compute_config_hash(config1)
    hash2 = compute_config_hash(config2)
    
    assert hash1 == hash2
    assert len(hash1) == 8


def test_compute_config_hash_different():
    """Test that different configs produce different hashes."""
    config1 = {"enable_cleaning": True}
    config2 = {"enable_cleaning": False}
    
    hash1 = compute_config_hash(config1)
    hash2 = compute_config_hash(config2)
    
    assert hash1 != hash2


def test_compute_config_hash_empty():
    """Test that empty config returns empty string."""
    assert compute_config_hash({}) == ""
    assert compute_config_hash(None) == ""
```

- [ ] **Step 3: 运行配置哈希测试**

Run: `pytest tests/unit/test_performance_cache.py::test_compute_config_hash_consistent -v`
Expected: PASS

- [ ] **Step 4: 编写缓存键隔离测试**

```python
def test_cache_with_different_configs(cache, sample_pdf):
    """Test that different configs use different cache keys."""
    config1 = {"enable_cleaning": True}
    config2 = {"enable_cleaning": False}
    
    # Set cache with config1
    cache.set(sample_pdf, "docling", {"result": "data1"}, config1)
    
    # Set cache with config2
    cache.set(sample_pdf, "docling", {"result": "data2"}, config2)
    
    # Get with config1
    result1 = cache.get(sample_pdf, "docling", config1)
    assert result1 == {"result": "data1"}
    
    # Get with config2
    result2 = cache.get(sample_pdf, "docling", config2)
    assert result2 == {"result": "data2"}


def test_cache_hit_and_miss(cache, sample_pdf):
    """Test cache hit and miss scenarios."""
    # Miss - no cache exists
    result = cache.get(sample_pdf, "docling")
    assert result is None
    
    # Set cache
    test_data = {"pages": 10, "content": "test"}
    cache.set(sample_pdf, "docling", test_data)
    
    # Hit - cache exists
    result = cache.get(sample_pdf, "docling")
    assert result == test_data
```

- [ ] **Step 5: 运行缓存隔离测试**

Run: `pytest tests/unit/test_performance_cache.py::test_cache_with_different_configs -v`
Expected: PASS

- [ ] **Step 6: 编写原子写入测试**

```python
def test_cache_atomic_write(cache, sample_pdf):
    """Test that cache writes are atomic (no corruption)."""
    import threading
    
    def write_cache(value):
        cache.set(sample_pdf, "test", {"value": value})
    
    # Concurrent writes
    threads = []
    for i in range(10):
        t = threading.Thread(target=write_cache, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Read cache - should be valid JSON
    result = cache.get(sample_pdf, "test")
    assert result is not None
    assert "value" in result
    assert isinstance(result["value"], int)


def test_cache_clear_operations(cache, sample_pdf, tmp_path):
    """Test cache clearing functionality."""
    # Create multiple cache entries
    cache.set(sample_pdf, "op1", {"data": 1})
    cache.set(sample_pdf, "op2", {"data": 2})
    
    pdf2 = tmp_path / "another.pdf"
    pdf2.write_bytes(b"%PDF-1.4\nother")
    cache.set(pdf2, "op1", {"data": 3})
    
    # Clear specific file
    cache.clear(sample_pdf)
    
    assert cache.get(sample_pdf, "op1") is None
    assert cache.get(sample_pdf, "op2") is None
    assert cache.get(pdf2, "op1") == {"data": 3}
    
    # Clear all
    cache.clear()
    assert cache.get(pdf2, "op1") is None
```

- [ ] **Step 7: 运行所有缓存测试**

Run: `pytest tests/unit/test_performance_cache.py -v`
Expected: All tests PASS

- [ ] **Step 8: 提交缓存测试**

```bash
git add tests/unit/test_performance_cache.py
git commit -m "test: add unit tests for PDF processing cache

- Test config hash consistency and isolation
- Test cache hit/miss scenarios
- Test atomic write safety
- Test cache clearing operations"
```

---

### Task 2: 图表提取单元测试

**Files:**
- Create: `tests/unit/test_chart_extractor.py`
- Test: `app/ingestion/utils/chart_extractor.py`

- [ ] **Step 1: 创建测试文件和fixtures**

```python
"""Unit tests for chart extraction utilities."""

import pytest
from io import BytesIO
from PIL import Image
from app.ingestion.utils.chart_extractor import (
    _resize_image_if_needed,
    detect_chart_in_image,
    MAX_IMAGE_SIZE_BYTES
)


@pytest.fixture
def small_image_bytes():
    """Create a small test image (< 5MB)."""
    img = Image.new('RGB', (800, 600), color='white')
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    return buffer.getvalue()


@pytest.fixture
def large_image_bytes():
    """Create a large test image (> 5MB)."""
    # Create 3000x3000 image
    img = Image.new('RGB', (3000, 3000), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def chart_like_image_bytes():
    """Create an image that looks like a chart."""
    # 1000x800 image (reasonable chart dimensions)
    img = Image.new('RGB', (1000, 800), color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()
```

- [ ] **Step 2: 编写图片缩放测试**

```python
def test_image_resize_small_image(small_image_bytes):
    """Test that small images are not resized."""
    original_size = len(small_image_bytes)
    result = _resize_image_if_needed(small_image_bytes)
    
    assert len(result) == original_size
    assert result == small_image_bytes


def test_image_resize_large_image(large_image_bytes):
    """Test that large images are resized to fit limit."""
    original_size = len(large_image_bytes)
    assert original_size > MAX_IMAGE_SIZE_BYTES
    
    result = _resize_image_if_needed(large_image_bytes)
    
    assert len(result) <= MAX_IMAGE_SIZE_BYTES
    assert len(result) < original_size
    
    # Verify it's still a valid image
    img = Image.open(BytesIO(result))
    assert img.format == 'JPEG'


def test_image_resize_preserves_aspect_ratio(large_image_bytes):
    """Test that resizing preserves aspect ratio."""
    original_img = Image.open(BytesIO(large_image_bytes))
    original_ratio = original_img.width / original_img.height
    
    result = _resize_image_if_needed(large_image_bytes)
    resized_img = Image.open(BytesIO(result))
    resized_ratio = resized_img.width / resized_img.height
    
    assert abs(original_ratio - resized_ratio) < 0.01
```

- [ ] **Step 3: 运行图片缩放测试**

Run: `pytest tests/unit/test_chart_extractor.py::test_image_resize_large_image -v`
Expected: PASS

- [ ] **Step 4: 编写图表检测测试**

```python
def test_chart_detection_reasonable_size(chart_like_image_bytes):
    """Test that reasonably-sized images pass basic detection."""
    result = detect_chart_in_image(chart_like_image_bytes)
    
    assert "is_chart" in result
    assert "chart_type" in result
    assert "confidence" in result
    assert isinstance(result["is_chart"], bool)


def test_chart_detection_too_small():
    """Test that very small images are rejected."""
    # 100x100 image (too small for chart)
    img = Image.new('RGB', (100, 100), color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    result = detect_chart_in_image(buffer.getvalue())
    
    assert result["is_chart"] is False
    assert result["confidence"] == 0.0


def test_chart_detection_bad_aspect_ratio():
    """Test that images with extreme aspect ratios are rejected."""
    # Very wide image (10:1 ratio)
    img = Image.new('RGB', (2000, 200), color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    
    result = detect_chart_in_image(buffer.getvalue())
    
    assert result["is_chart"] is False or result["confidence"] < 0.5
```

- [ ] **Step 5: 运行图表检测测试**

Run: `pytest tests/unit/test_chart_extractor.py -k detection -v`
Expected: All detection tests PASS

- [ ] **Step 6: 编写Vision API错误处理测试**

```python
from unittest.mock import patch, Mock


def test_vision_api_missing_key():
    """Test handling of missing API key."""
    from app.ingestion.utils.chart_extractor import extract_chart_data_with_vision
    
    result = extract_chart_data_with_vision(
        b"fake_image_data",
        model="gpt-4o",
        api_key=None
    )
    
    assert "error" in result
    assert "api_key" in result["error"].lower() or "key" in result["error"].lower()


@patch('app.ingestion.utils.chart_extractor.OpenAI')
def test_vision_api_network_error(mock_openai, small_image_bytes):
    """Test handling of network errors."""
    from app.ingestion.utils.chart_extractor import extract_chart_data_with_vision
    
    # Mock network error
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = Exception("Network timeout")
    mock_openai.return_value = mock_client
    
    result = extract_chart_data_with_vision(
        small_image_bytes,
        model="gpt-4o",
        api_key="test_key"
    )
    
    assert "error" in result
```

- [ ] **Step 7: 运行所有图表提取测试**

Run: `pytest tests/unit/test_chart_extractor.py -v`
Expected: All tests PASS

- [ ] **Step 8: 提交图表提取测试**

```bash
git add tests/unit/test_chart_extractor.py
git commit -m "test: add unit tests for chart extraction

- Test image resizing with 5MB limit
- Test aspect ratio preservation
- Test chart detection heuristics
- Test Vision API error handling"
```

---

### Task 3: 工具函数单元测试

**Files:**
- Create: `tests/unit/test_pdf_utils.py`
- Test: `app/ingestion/utils/performance.py`

- [ ] **Step 1: 创建工具函数测试文件**

```python
"""Unit tests for PDF utility functions."""

import pytest
import hashlib
from pathlib import Path
from app.ingestion.utils.performance import compute_file_hash


@pytest.fixture
def test_file(tmp_path):
    """Create a test file with known content."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content for hashing")
    return file_path


def test_compute_file_hash_consistent(test_file):
    """Test that same file produces same hash."""
    hash1 = compute_file_hash(test_file)
    hash2 = compute_file_hash(test_file)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_compute_file_hash_different_content(tmp_path):
    """Test that different files produce different hashes."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    
    file1.write_text("content A")
    file2.write_text("content B")
    
    hash1 = compute_file_hash(file1)
    hash2 = compute_file_hash(file2)
    
    assert hash1 != hash2


def test_compute_file_hash_large_file(tmp_path):
    """Test hashing of large files (chunked reading)."""
    large_file = tmp_path / "large.bin"
    
    # Create 10MB file
    large_file.write_bytes(b"x" * (10 * 1024 * 1024))
    
    hash_result = compute_file_hash(large_file)
    
    assert len(hash_result) == 64
    assert hash_result.isalnum()
```

- [ ] **Step 2: 运行工具函数测试**

Run: `pytest tests/unit/test_pdf_utils.py -v`
Expected: All tests PASS

- [ ] **Step 3: 提交工具函数测试**

```bash
git add tests/unit/test_pdf_utils.py
git commit -m "test: add unit tests for PDF utility functions

- Test file hash consistency
- Test hash uniqueness for different files
- Test large file handling"
```

---

### Task 4: 性能基准测试系统

**Files:**
- Create: `tests/performance/benchmark_pdf_processing.py`
- Create: `tests/performance/__init__.py`

- [ ] **Step 1: 创建性能测试目录和基础文件**

```python
"""Performance benchmarking for PDF processing."""

import time
import json
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PDFBenchmark:
    """Benchmark PDF processing performance."""
    
    def __init__(self, results_file: Path = Path("tests/performance/benchmark_results.json")):
        self.results_file = results_file
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        self.process = psutil.Process()
    
    def benchmark_loader(
        self,
        pdf_path: Path,
        loader_func,
        mode: str
    ) -> Dict:
        """
        Benchmark a single PDF loader.
        
        Args:
            pdf_path: Path to PDF file
            loader_func: Loader function to benchmark
            mode: Processing mode name
            
        Returns:
            Benchmark results dict
        """
        # Record initial memory
        mem_before = self.process.memory_info().rss / 1024 / 1024
        
        # Execute loader
        start = time.time()
        try:
            docs = loader_func(pdf_path)
            duration = time.time() - start
            success = True
            error = None
        except Exception as e:
            duration = time.time() - start
            docs = []
            success = False
            error = str(e)
        
        # Record peak memory
        mem_after = self.process.memory_info().rss / 1024 / 1024
        mem_peak = mem_after - mem_before
        
        return {
            "mode": mode,
            "file_name": pdf_path.name,
            "file_size_mb": pdf_path.stat().st_size / 1024 / 1024,
            "time_seconds": round(duration, 2),
            "memory_mb": round(mem_peak, 2),
            "num_docs": len(docs),
            "success": success,
            "error": error
        }
    
    def save_results(self, results: List[Dict]):
        """Save benchmark results to JSON file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": results
        }
        
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Benchmark results saved to {self.results_file}")
```

- [ ] **Step 2: 添加基准测试运行函数**

```python
def run_benchmarks(pdf_files: List[Path]) -> List[Dict]:
    """
    Run benchmarks on multiple PDF files.
    
    Args:
        pdf_files: List of PDF files to benchmark
        
    Returns:
        List of benchmark results
    """
    from app.ingestion.loaders import load_pdf_text
    from app.ingestion.loaders.pdf_loader_enhanced import load_pdf_enhanced
    
    benchmark = PDFBenchmark()
    results = []
    
    for pdf_path in pdf_files:
        if not pdf_path.exists():
            logger.warning(f"PDF not found: {pdf_path}")
            continue
        
        logger.info(f"Benchmarking {pdf_path.name}...")
        
        # Benchmark pypdf (basic)
        result = benchmark.benchmark_loader(
            pdf_path,
            load_pdf_text,
            "pypdf"
        )
        results.append(result)
        
        # Benchmark docling_enhanced
        result = benchmark.benchmark_loader(
            pdf_path,
            lambda p: load_pdf_enhanced(p, by_page=True),
            "docling_enhanced"
        )
        results.append(result)
    
    # Save results
    benchmark.save_results(results)
    
    return results


def print_summary(results: List[Dict]):
    """Print benchmark summary."""
    print("\n" + "="*60)
    print("PDF Processing Benchmark Results")
    print("="*60)
    
    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"\n{status} {result['file_name']} - {result['mode']}")
        print(f"  Time: {result['time_seconds']}s")
        print(f"  Memory: {result['memory_mb']}MB")
        print(f"  Docs: {result['num_docs']}")
        if result['error']:
            print(f"  Error: {result['error']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python benchmark_pdf_processing.py <pdf_file1> [pdf_file2] ...")
        sys.exit(1)
    
    pdf_files = [Path(p) for p in sys.argv[1:]]
    results = run_benchmarks(pdf_files)
    print_summary(results)
```

- [ ] **Step 3: 创建__init__.py**

```python
"""Performance testing package."""
```

- [ ] **Step 4: 测试基准测试系统（如果有测试PDF）**

Run: `python tests/performance/benchmark_pdf_processing.py data/sample.pdf` (如果存在测试PDF)
Expected: 输出基准测试结果，创建benchmark_results.json

- [ ] **Step 5: 提交性能基准测试**

```bash
git add tests/performance/
git commit -m "test: add performance benchmarking system

- Benchmark PDF loader performance
- Track time, memory, and document count
- Save results to JSON for tracking
- Support multiple PDF files and modes"
```

---

### Task 5: 更新pytest配置

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: 检查conftest.py是否存在**

Run: `test -f tests/conftest.py && echo "exists" || echo "not found"`
Expected: "exists" 或 "not found"

- [ ] **Step 2: 添加PDF测试fixtures（如果conftest.py存在则追加，否则创建）**

```python
# 追加到 tests/conftest.py

import pytest
from pathlib import Path


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Provide a sample PDF file path for testing."""
    pdf_path = tmp_path / "test_sample.pdf"
    # Create minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
190
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def mock_openai_response():
    """Provide a mock OpenAI API response for testing."""
    return {
        "chart_type": "bar",
        "title": "Test Chart",
        "data": [{"x": "A", "y": 10}, {"x": "B", "y": 20}]
    }
```

- [ ] **Step 3: 运行所有单元测试验证fixtures**

Run: `pytest tests/unit/ -v`
Expected: All tests PASS

- [ ] **Step 4: 提交conftest更新**

```bash
git add tests/conftest.py
git commit -m "test: add PDF testing fixtures to conftest

- Add sample_pdf_path fixture for test PDFs
- Add mock_openai_response fixture for API mocking"
```

---

### Task 6: 运行完整测试套件并生成覆盖率报告

**Files:**
- Test: All unit tests

- [ ] **Step 1: 安装测试依赖（如果需要）**

Run: `pip install pytest pytest-cov pytest-mock psutil`
Expected: Dependencies installed

- [ ] **Step 2: 运行所有单元测试**

Run: `pytest tests/unit/ -v`
Expected: All tests PASS

- [ ] **Step 3: 生成覆盖率报告**

Run: `pytest tests/unit/ --cov=app.ingestion.utils --cov-report=term --cov-report=html`
Expected: Coverage report generated, target ≥ 80%

- [ ] **Step 4: 查看覆盖率结果**

Run: `pytest tests/unit/ --cov=app.ingestion.utils --cov-report=term`
Expected: 显示覆盖率百分比

- [ ] **Step 5: 提交第1周完成标记**

```bash
git add .
git commit -m "test: complete Week 1 - testing infrastructure

Week 1 deliverables:
- Unit tests for cache system (config isolation, atomic writes)
- Unit tests for chart extraction (resize, detection, error handling)
- Unit tests for utility functions (file hashing)
- Performance benchmarking system
- Test fixtures and pytest configuration

Coverage: [X]% of app.ingestion.utils"
```

---

## 验证清单

完成第1周后，验证以下内容：

- [ ] 所有单元测试通过
- [ ] 测试覆盖率 ≥ 80%
- [ ] 性能基准测试可运行
- [ ] 测试fixtures正常工作
- [ ] 所有代码已提交

## 下一步

第1周完成后，继续第2周：错误场景测试 + 批量图表提取
