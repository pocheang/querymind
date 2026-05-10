"""Performance optimization for PDF processing - parallel processing and caching."""

import hashlib
import json
from pathlib import Path
from typing import List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of file for caching.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of file hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


class PDFProcessingCache:
    """Cache for PDF processing results."""

    def __init__(self, cache_dir: Path = Path("./data/cache/pdf_processing")):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, file_path: Path, operation: str) -> Path:
        """Get cache file path for a PDF and operation."""
        file_hash = compute_file_hash(file_path)
        cache_file = f"{file_hash}_{operation}.json"
        return self.cache_dir / cache_file

    def get(self, file_path: Path, operation: str) -> Optional[Any]:
        """
        Get cached result.

        Args:
            file_path: Path to PDF file
            operation: Operation name (e.g., 'docling', 'ocr', 'charts')

        Returns:
            Cached result or None
        """
        cache_path = self.get_cache_path(file_path, operation)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Cache hit for {file_path.name} - {operation}")
                return data
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
            return None

    def set(self, file_path: Path, operation: str, result: Any) -> None:
        """
        Cache result.

        Args:
            file_path: Path to PDF file
            operation: Operation name
            result: Result to cache (must be JSON serializable)
        """
        cache_path = self.get_cache_path(file_path, operation)

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                logger.info(f"Cached result for {file_path.name} - {operation}")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def clear(self, file_path: Optional[Path] = None) -> None:
        """
        Clear cache.

        Args:
            file_path: If provided, clear cache for this file only.
                      If None, clear all cache.
        """
        if file_path:
            file_hash = compute_file_hash(file_path)
            for cache_file in self.cache_dir.glob(f"{file_hash}_*.json"):
                cache_file.unlink()
                logger.info(f"Cleared cache for {file_path.name}")
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared all cache")


def process_pdfs_parallel(
    pdf_paths: List[Path],
    process_func: Callable[[Path], Any],
    max_workers: int = 4,
    use_processes: bool = False
) -> List[Any]:
    """
    Process multiple PDFs in parallel.

    Args:
        pdf_paths: List of PDF file paths
        process_func: Function to process each PDF
        max_workers: Maximum number of parallel workers
        use_processes: Use ProcessPoolExecutor instead of ThreadPoolExecutor

    Returns:
        List of results in same order as input
    """
    if len(pdf_paths) == 1:
        # No need for parallel processing
        return [process_func(pdf_paths[0])]

    executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

    results = [None] * len(pdf_paths)

    with executor_class(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_func, pdf_path): i
            for i, pdf_path in enumerate(pdf_paths)
        }

        # Collect results as they complete
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results[index] = result
                logger.info(f"Completed {index + 1}/{len(pdf_paths)}")
            except Exception as e:
                logger.error(f"Processing failed for {pdf_paths[index]}: {e}")
                results[index] = None

    return results


def process_pages_parallel(
    pages_data: List[Any],
    process_func: Callable[[Any], Any],
    max_workers: int = 4
) -> List[Any]:
    """
    Process multiple pages in parallel.

    Args:
        pages_data: List of page data
        process_func: Function to process each page
        max_workers: Maximum number of parallel workers

    Returns:
        List of results in same order as input
    """
    if len(pages_data) <= 1:
        return [process_func(page) for page in pages_data]

    results = [None] * len(pages_data)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(process_func, page): i
            for i, page in enumerate(pages_data)
        }

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                logger.error(f"Page {index} processing failed: {e}")
                results[index] = None

    return results


def estimate_processing_time(
    file_path: Path,
    mode: str = "docling_enhanced"
) -> float:
    """
    Estimate processing time for a PDF.

    Args:
        file_path: Path to PDF file
        mode: Processing mode

    Returns:
        Estimated time in seconds
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        num_pages = len(reader.pages)
    except Exception:
        # Fallback estimate based on file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        num_pages = int(file_size_mb * 2)  # Rough estimate

    # Time estimates per page (seconds)
    time_per_page = {
        "pypdf": 0.5,
        "docling": 3.0,
        "docling_enhanced": 4.0,
        "hybrid": 5.0
    }

    base_time = num_pages * time_per_page.get(mode, 3.0)

    # Add overhead
    overhead = 2.0  # seconds

    return base_time + overhead


def should_use_parallel(pdf_paths: List[Path], threshold: int = 3) -> bool:
    """
    Determine if parallel processing is beneficial.

    Args:
        pdf_paths: List of PDF paths
        threshold: Minimum number of files to use parallel processing

    Returns:
        True if parallel processing should be used
    """
    return len(pdf_paths) >= threshold
