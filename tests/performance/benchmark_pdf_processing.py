"""Performance benchmarking for PDF processing."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


class PDFBenchmark:
    """Benchmark PDF processing performance."""

    def __init__(self, results_file: Path = Path("tests/performance/benchmark_results.json")):
        self.results_file = results_file
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        self.process = psutil.Process()

    def benchmark_loader(self, pdf_path: Path, loader_func, mode: str) -> dict:
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
            "error": error,
        }

    def benchmark_cache_operations(self, cache, pdf_path: Path, num_iterations: int = 100) -> dict:
        """
        Benchmark cache set/get operations.

        Args:
            cache: PDFProcessingCache instance
            pdf_path: Path to PDF file
            num_iterations: Number of iterations to run

        Returns:
            Benchmark results dict
        """
        test_data = {"pages": 10, "content": "test" * 100}

        # Benchmark cache set
        start = time.time()
        for i in range(num_iterations):
            cache.set(pdf_path, f"op_{i}", test_data)
        set_duration = time.time() - start

        # Benchmark cache get
        start = time.time()
        for i in range(num_iterations):
            cache.get(pdf_path, f"op_{i}")
        get_duration = time.time() - start

        return {
            "operation": "cache_operations",
            "iterations": num_iterations,
            "set_time_seconds": round(set_duration, 3),
            "get_time_seconds": round(get_duration, 3),
            "avg_set_ms": round((set_duration / num_iterations) * 1000, 2),
            "avg_get_ms": round((get_duration / num_iterations) * 1000, 2),
        }

    def benchmark_chart_extraction(self, image_bytes: bytes, num_iterations: int = 10) -> dict:
        """
        Benchmark chart extraction operations.

        Args:
            image_bytes: Image data to process
            num_iterations: Number of iterations to run

        Returns:
            Benchmark results dict
        """
        from app.ingestion.utils.chart_extractor import detect_chart_in_image

        mem_before = self.process.memory_info().rss / 1024 / 1024

        start = time.time()
        for _ in range(num_iterations):
            detect_chart_in_image(image_bytes)
        duration = time.time() - start

        mem_after = self.process.memory_info().rss / 1024 / 1024
        mem_peak = mem_after - mem_before

        return {
            "operation": "chart_extraction",
            "iterations": num_iterations,
            "total_time_seconds": round(duration, 2),
            "avg_time_ms": round((duration / num_iterations) * 1000, 2),
            "memory_mb": round(mem_peak, 2),
        }

    def benchmark_sequential_chart_extraction(
        self, images: list[bytes], mock_api_delay: float = 0.1, warmup_runs: int = 1
    ) -> dict:
        """
        Benchmark sequential chart extraction (baseline).

        Args:
            images: List of image bytes to process
            mock_api_delay: Simulated API call delay in seconds
            warmup_runs: Number of warmup iterations before timing (default: 1)

        Returns:
            Benchmark results dict
        """
        from unittest.mock import patch

        num_images = len(images)

        # Mock the API call to return consistent results with controlled timing
        def mock_extract(image_bytes, model="gpt-4o", api_key=None):
            time.sleep(mock_api_delay)  # Simulate API latency
            return {
                "chart_type": "bar",
                "title": "Test Chart",
                "data": [{"label": "A", "value": 10}],
                "description": "Mock chart data",
            }

        # Patch both the internal functions to avoid actual API calls
        with (
            patch("app.ingestion.utils.chart_extractor._extract_with_openai", side_effect=mock_extract),
            patch("app.ingestion.utils.chart_extractor._extract_with_anthropic", side_effect=mock_extract),
        ):
            from app.ingestion.utils.chart_extractor import extract_chart_data_with_vision

            # Warmup runs to eliminate first-run overhead
            for _ in range(warmup_runs):
                for img in images:
                    extract_chart_data_with_vision(img, model="gpt-4o", api_key="mock_key")

            # Actual timed run
            mem_before = self.process.memory_info().rss / 1024 / 1024
            start = time.time()
            results = []

            for img in images:
                result = extract_chart_data_with_vision(img, model="gpt-4o", api_key="mock_key")
                results.append(result)

            duration = time.time() - start
            mem_after = self.process.memory_info().rss / 1024 / 1024
            mem_peak = mem_after - mem_before

        return {
            "operation": "sequential_chart_extraction",
            "num_images": num_images,
            "total_time_seconds": round(duration, 3),
            "avg_time_per_image_ms": round((duration / num_images) * 1000, 2),
            "memory_mb": round(mem_peak, 2),
            "success_count": len([r for r in results if "error" not in r]),
        }

    def benchmark_batch_chart_extraction(
        self, images: list[bytes], batch_size: int = 5, mock_api_delay: float = 0.1, warmup_runs: int = 1
    ) -> dict:
        """
        Benchmark batch chart extraction (optimized).

        Args:
            images: List of image bytes to process
            batch_size: Number of concurrent API calls
            mock_api_delay: Simulated API call delay in seconds
            warmup_runs: Number of warmup iterations before timing (default: 1)

        Returns:
            Benchmark results dict
        """
        import asyncio
        from unittest.mock import patch

        num_images = len(images)

        # Mock the API call to return consistent results with controlled timing
        def mock_extract(image_bytes, model="gpt-4o", api_key=None):
            time.sleep(mock_api_delay)  # Simulate API latency
            return {
                "chart_type": "bar",
                "title": "Test Chart",
                "data": [{"label": "A", "value": 10}],
                "description": "Mock chart data",
            }

        # Patch both the internal functions to avoid actual API calls
        with (
            patch("app.ingestion.utils.chart_extractor._extract_with_openai", side_effect=mock_extract),
            patch("app.ingestion.utils.chart_extractor._extract_with_anthropic", side_effect=mock_extract),
        ):
            from app.ingestion.utils.batch_chart_extractor import BatchChartExtractor

            # Warmup runs to eliminate first-run overhead
            for _ in range(warmup_runs):
                extractor = BatchChartExtractor(batch_size=batch_size)
                asyncio.run(extractor.extract_charts_batch(images, model="gpt-4o", api_key="mock_key"))
                extractor._executor.shutdown(wait=True)

            # Actual timed run
            mem_before = self.process.memory_info().rss / 1024 / 1024
            start = time.time()

            extractor = BatchChartExtractor(batch_size=batch_size)
            results = asyncio.run(extractor.extract_charts_batch(images, model="gpt-4o", api_key="mock_key"))
            extractor._executor.shutdown(wait=True)

            duration = time.time() - start
            mem_after = self.process.memory_info().rss / 1024 / 1024
            mem_peak = mem_after - mem_before

        return {
            "operation": "batch_chart_extraction",
            "num_images": num_images,
            "batch_size": batch_size,
            "total_time_seconds": round(duration, 3),
            "avg_time_per_image_ms": round((duration / num_images) * 1000, 2),
            "memory_mb": round(mem_peak, 2),
            "success_count": len([r for r in results if "error" not in r]),
        }

    def benchmark_chart_extraction_comparison(
        self, num_images: int = 10, batch_size: int = 5, mock_api_delay: float = 0.1
    ) -> dict:
        """
        Compare sequential vs batch chart extraction performance.

        Args:
            num_images: Number of images to process
            batch_size: Batch size for concurrent processing
            mock_api_delay: Simulated API call delay in seconds

        Returns:
            Comparison results dict with speedup metrics
        """
        from io import BytesIO

        from PIL import Image

        # Create test images
        images = []
        for i in range(num_images):
            img = Image.new("RGB", (800, 600), color=(i * 10 % 255, 100, 150))
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            images.append(buffer.getvalue())

        logger.info(f"Benchmarking chart extraction: {num_images} images, batch_size={batch_size}")

        # Benchmark sequential
        sequential_result = self.benchmark_sequential_chart_extraction(images, mock_api_delay)

        # Benchmark batch
        batch_result = self.benchmark_batch_chart_extraction(images, batch_size, mock_api_delay)

        # Calculate speedup metrics
        sequential_time = sequential_result["total_time_seconds"]
        batch_time = batch_result["total_time_seconds"]
        speedup_factor = sequential_time / batch_time if batch_time > 0 else 0
        time_saved = sequential_time - batch_time
        time_saved_percent = (time_saved / sequential_time * 100) if sequential_time > 0 else 0

        # Check if meets 40% improvement target (speedup >= 1.67x)
        meets_target = speedup_factor >= 1.67

        return {
            "operation": "chart_extraction_comparison",
            "num_images": num_images,
            "batch_size": batch_size,
            "sequential": sequential_result,
            "batch": batch_result,
            "speedup_factor": round(speedup_factor, 2),
            "time_saved_seconds": round(time_saved, 3),
            "time_saved_percent": round(time_saved_percent, 1),
            "meets_40_percent_target": meets_target,
            "target_speedup": 1.67,
        }

    def save_results(self, results: list[dict]):
        """Save benchmark results to JSON file."""
        output = {"timestamp": datetime.now().isoformat(), "benchmarks": results}

        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Benchmark results saved to {self.results_file}")


def run_benchmarks(pdf_files: list[Path]) -> list[dict]:
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
        result = benchmark.benchmark_loader(pdf_path, load_pdf_text, "pypdf")
        results.append(result)

        # Benchmark docling_enhanced
        result = benchmark.benchmark_loader(pdf_path, lambda p: load_pdf_enhanced(p, by_page=True), "docling_enhanced")
        results.append(result)

    # Save results
    benchmark.save_results(results)

    return results


def run_cache_benchmark(pdf_path: Path, num_iterations: int = 100) -> dict:
    """
    Run cache performance benchmark.

    Args:
        pdf_path: Path to PDF file for cache testing
        num_iterations: Number of iterations

    Returns:
        Benchmark results dict
    """
    import tempfile

    from app.ingestion.utils.performance import PDFProcessingCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = PDFProcessingCache(cache_dir=Path(tmpdir))
        benchmark = PDFBenchmark()
        return benchmark.benchmark_cache_operations(cache, pdf_path, num_iterations)


def run_chart_extraction_benchmark(num_iterations: int = 10) -> dict:
    """
    Run chart extraction performance benchmark.

    Args:
        num_iterations: Number of iterations

    Returns:
        Benchmark results dict
    """
    from io import BytesIO

    from PIL import Image

    # Create test image
    img = Image.new("RGB", (1000, 800), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    benchmark = PDFBenchmark()
    return benchmark.benchmark_chart_extraction(image_bytes, num_iterations)


def run_batch_chart_extraction_benchmark(
    num_images: int = 10, batch_size: int = 5, mock_api_delay: float = 0.1
) -> dict:
    """
    Run batch chart extraction comparison benchmark.

    Args:
        num_images: Number of images to process
        batch_size: Batch size for concurrent processing
        mock_api_delay: Simulated API call delay in seconds

    Returns:
        Comparison benchmark results dict
    """
    benchmark = PDFBenchmark()
    return benchmark.benchmark_chart_extraction_comparison(
        num_images=num_images, batch_size=batch_size, mock_api_delay=mock_api_delay
    )


def run_batch_size_comparison(
    num_images: int = 20, batch_sizes: list[int] = None, mock_api_delay: float = 0.1
) -> list[dict]:
    """
    Compare performance across different batch sizes.

    Args:
        num_images: Number of images to process
        batch_sizes: List of batch sizes to test (default: [1, 5, 10, 20])
        mock_api_delay: Simulated API call delay in seconds

    Returns:
        List of comparison results for each batch size
    """
    if batch_sizes is None:
        batch_sizes = [1, 5, 10, 20]

    benchmark = PDFBenchmark()
    results = []

    for batch_size in batch_sizes:
        logger.info(f"\nTesting batch_size={batch_size}")
        result = benchmark.benchmark_chart_extraction_comparison(
            num_images=num_images, batch_size=batch_size, mock_api_delay=mock_api_delay
        )
        results.append(result)

    return results


def print_summary(results: list[dict]):
    """Print benchmark summary."""
    print("\n" + "=" * 60)
    print("PDF Processing Benchmark Results")
    print("=" * 60)

    for result in results:
        if "operation" in result:
            operation = result["operation"]

            if operation == "chart_extraction_comparison":
                # Special formatting for comparison results
                print(f"\n{operation.upper().replace('_', ' ')}")
                print(f"  Images: {result['num_images']}")
                print(f"  Batch Size: {result['batch_size']}")
                print("\n  Sequential Processing:")
                print(f"    Time: {result['sequential']['total_time_seconds']}s")
                print(f"    Avg per image: {result['sequential']['avg_time_per_image_ms']}ms")
                print(f"    Memory: {result['sequential']['memory_mb']}MB")
                print("\n  Batch Processing:")
                print(f"    Time: {result['batch']['total_time_seconds']}s")
                print(f"    Avg per image: {result['batch']['avg_time_per_image_ms']}ms")
                print(f"    Memory: {result['batch']['memory_mb']}MB")
                print("\n  Performance Improvement:")
                print(f"    Speedup Factor: {result['speedup_factor']}x")
                print(f"    Time Saved: {result['time_saved_seconds']}s ({result['time_saved_percent']}%)")
                target_status = "✓ PASS" if result["meets_40_percent_target"] else "✗ FAIL"
                print(f"    Meets 40% Target: {target_status}")
            else:
                # Cache or other chart extraction benchmark
                print(f"\n{operation.upper().replace('_', ' ')}")
                for key, value in result.items():
                    if key != "operation" and not isinstance(value, dict):
                        print(f"  {key}: {value}")
        else:
            # PDF loader benchmark
            status = "✓" if result["success"] else "✗"
            print(f"\n{status} {result['file_name']} - {result['mode']}")
            print(f"  Time: {result['time_seconds']}s")
            print(f"  Memory: {result['memory_mb']}MB")
            print(f"  Docs: {result['num_docs']}")
            if result["error"]:
                print(f"  Error: {result['error']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python benchmark_pdf_processing.py <pdf_file1> [pdf_file2] ...")
        sys.exit(1)

    pdf_files = [Path(p) for p in sys.argv[1:]]
    results = run_benchmarks(pdf_files)
    print_summary(results)
