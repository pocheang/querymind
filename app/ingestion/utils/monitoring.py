import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class PDFProcessingMetrics:
    """Collects and analyzes PDF processing metrics."""

    def __init__(self, metrics_file: Path = Path("./data/metrics/pdf_processing.jsonl")):
        """Initialize metrics collection.

        Args:
            metrics_file: Path to JSONL file for storing metrics.
        """
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
    ) -> None:
        """Record a single PDF processing operation.

        Args:
            file_path: Path to the PDF file processed.
            mode: Processing mode (e.g., 'streaming', 'batch').
            duration: Processing duration in seconds.
            memory_mb: Memory used in MB.
            cache_hit: Whether the result was from cache.
            api_calls: Number of API calls made.
            num_pages: Number of pages in the PDF.
            error: Error message if processing failed, None otherwise.
        """
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

        with open(self.metrics_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metric, ensure_ascii=False) + '\n')

    def get_summary(self, days: int = 7) -> Dict:
        """Get summary statistics for metrics within the specified time window.

        Args:
            days: Number of days to look back.

        Returns:
            Dictionary with summary statistics, or empty dict if no metrics found.
        """
        if not self.metrics_file.exists():
            return {}

        cutoff = datetime.now() - timedelta(days=days)
        metrics = []

        try:
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        metric = json.loads(line)
                        timestamp = datetime.fromisoformat(metric["timestamp"])
                        if timestamp >= cutoff:
                            metrics.append(metric)
        except (json.JSONDecodeError, IOError):
            return {}

        if not metrics:
            return {}

        # Calculate statistics
        total_processed = len(metrics)
        avg_time_seconds = sum(m["duration_seconds"] for m in metrics) / total_processed
        cache_hits = sum(1 for m in metrics if m["cache_hit"])
        cache_hit_rate = cache_hits / total_processed if total_processed > 0 else 0
        total_api_calls = sum(m["api_calls"] for m in metrics)
        estimated_cost_usd = total_api_calls * 0.01
        errors = sum(1 for m in metrics if m["error"] is not None)
        error_rate = errors / total_processed if total_processed > 0 else 0

        return {
            "period_days": days,
            "total_processed": total_processed,
            "avg_time_seconds": avg_time_seconds,
            "cache_hit_rate": cache_hit_rate,
            "total_api_calls": total_api_calls,
            "estimated_cost_usd": estimated_cost_usd,
            "error_rate": error_rate
        }
