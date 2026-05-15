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

    def benchmark_cache_operations(self, cache, pdf_path: Path, num_iterations: int = 100) -> Dict:
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
            "avg_get_ms": round((get_duration / num_iterations) * 1000, 2)
        }

    def benchmark_chart_extraction(self, image_bytes: bytes, num_iterations: int = 10) -> Dict:
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
            "memory_mb": round(mem_peak, 2)
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


def run_cache_benchmark(pdf_path: Path, num_iterations: int = 100) -> Dict:
    """
    Run cache performance benchmark.

    Args:
        pdf_path: Path to PDF file for cache testing
        num_iterations: Number of iterations

    Returns:
        Benchmark results dict
    """
    from app.ingestion.utils.performance import PDFProcessingCache
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = PDFProcessingCache(cache_dir=Path(tmpdir))
        benchmark = PDFBenchmark()
        return benchmark.benchmark_cache_operations(cache, pdf_path, num_iterations)


def run_chart_extraction_benchmark(num_iterations: int = 10) -> Dict:
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
    img = Image.new('RGB', (1000, 800), color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    image_bytes = buffer.getvalue()

    benchmark = PDFBenchmark()
    return benchmark.benchmark_chart_extraction(image_bytes, num_iterations)


def print_summary(results: List[Dict]):
    """Print benchmark summary."""
    print("\n" + "="*60)
    print("PDF Processing Benchmark Results")
    print("="*60)

    for result in results:
        if "operation" in result:
            # Cache or chart extraction benchmark
            print(f"\n{result['operation'].upper()}")
            for key, value in result.items():
                if key != "operation":
                    print(f"  {key}: {value}")
        else:
            # PDF loader benchmark
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
