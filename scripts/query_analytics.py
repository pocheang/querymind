#!/usr/bin/env python3
"""
查询分析工具 - 分析系统查询统计和性能

功能:
    - 查询类型分布（PDF、通用RAG、Web搜索）
    - 分层执行统计（fast/balanced/deep）
    - 性能指标（延迟、缓存命中率）
    - 时间趋势分析

使用:
    python scripts/query_analytics.py --days 7
    python scripts/query_analytics.py --export stats.json
    python scripts/query_analytics.py --detailed
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.core.config import get_settings
    settings = get_settings()
    DB_PATH = Path(settings.app_db_path_str)
except Exception:
    DB_PATH = Path("./data/app.db")


def get_db_connection():
    """Get database connection."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Make sure the application has been run at least once.")
        sys.exit(1)

    return sqlite3.connect(DB_PATH)


def analyze_queries(days: int = 7, detailed: bool = False) -> dict[str, Any]:
    """
    Analyze query statistics.

    Args:
        days: Number of days to analyze
        detailed: Include detailed breakdown

    Returns:
        Dictionary with statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    stats = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days
        },
        "summary": {},
        "breakdown": {}
    }

    try:
        # Check if audit_logs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='audit_logs'
        """)

        if not cursor.fetchone():
            print("⚠️  No audit_logs table found. Query analytics requires audit logging.")
            return stats

        # Total queries
        cursor.execute("""
            SELECT COUNT(*) FROM audit_logs
            WHERE operation = 'query'
            AND timestamp >= ?
        """, (start_date.isoformat(),))

        total_queries = cursor.fetchone()[0]
        stats["summary"]["total_queries"] = total_queries

        if total_queries == 0:
            print(f"ℹ️  No queries found in the last {days} days.")
            return stats

        # Query type distribution (from metadata)
        cursor.execute("""
            SELECT metadata FROM audit_logs
            WHERE operation = 'query'
            AND timestamp >= ?
            AND metadata IS NOT NULL
        """, (start_date.isoformat(),))

        query_types = Counter()
        tiers = Counter()
        cache_hits = 0
        cache_total = 0
        latencies = []

        for row in cursor.fetchall():
            try:
                meta = json.loads(row[0])

                # Query type
                query_type = meta.get("query_type", "unknown")
                query_types[query_type] += 1

                # Tier
                tier = meta.get("tier", "unknown")
                tiers[tier] += 1

                # Cache
                if "cache_hit" in meta:
                    cache_total += 1
                    if meta["cache_hit"]:
                        cache_hits += 1

                # Latency
                if "latency_ms" in meta:
                    latencies.append(meta["latency_ms"])

            except (json.JSONDecodeError, KeyError):
                continue

        # Calculate statistics
        stats["breakdown"]["query_types"] = dict(query_types)
        stats["breakdown"]["tiers"] = dict(tiers)

        # Cache statistics
        if cache_total > 0:
            stats["summary"]["cache_hit_rate"] = round(cache_hits / cache_total * 100, 1)
        else:
            stats["summary"]["cache_hit_rate"] = 0.0

        # Latency statistics
        if latencies:
            latencies.sort()
            stats["summary"]["avg_latency_ms"] = round(sum(latencies) / len(latencies), 1)
            stats["summary"]["p50_latency_ms"] = latencies[len(latencies) // 2]
            stats["summary"]["p95_latency_ms"] = latencies[int(len(latencies) * 0.95)]
            stats["summary"]["p99_latency_ms"] = latencies[int(len(latencies) * 0.99)]

        # Daily trends (if detailed)
        if detailed:
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM audit_logs
                WHERE operation = 'query'
                AND timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, (start_date.isoformat(),))

            daily_counts = {}
            for row in cursor.fetchall():
                daily_counts[row[0]] = row[1]

            stats["daily_trend"] = daily_counts

    finally:
        conn.close()

    return stats


def print_stats(stats: dict[str, Any], detailed: bool = False):
    """Print statistics in a formatted way."""

    print("\n" + "=" * 60)
    print("📊 查询分析报告")
    print("=" * 60)

    period = stats["period"]
    print(f"\n📅 分析周期: {period['days']}天")
    print(f"   开始: {period['start'][:10]}")
    print(f"   结束: {period['end'][:10]}")

    summary = stats.get("summary", {})
    if not summary:
        print("\n⚠️  暂无查询数据")
        return

    print(f"\n📈 总体统计:")
    print(f"   总查询数: {summary.get('total_queries', 0):,}")

    if "avg_latency_ms" in summary:
        print(f"   平均响应: {summary['avg_latency_ms']}ms")
        print(f"   P95延迟: {summary['p95_latency_ms']}ms")

    if "cache_hit_rate" in summary:
        cache_rate = summary['cache_hit_rate']
        print(f"   缓存命中率: {cache_rate}%")

    # Query type breakdown
    breakdown = stats.get("breakdown", {})
    query_types = breakdown.get("query_types", {})

    if query_types:
        print(f"\n📋 查询类型分布:")
        total = sum(query_types.values())
        for qtype, count in sorted(query_types.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total * 100
            bar = "█" * int(percentage / 2)
            print(f"   {qtype:12} {count:5} ({percentage:5.1f}%) {bar}")

    # Tier breakdown
    tiers = breakdown.get("tiers", {})
    if tiers:
        print(f"\n⚡ 分层执行统计:")
        total = sum(tiers.values())
        for tier, count in sorted(tiers.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total * 100
            bar = "█" * int(percentage / 2)
            print(f"   {tier:12} {count:5} ({percentage:5.1f}%) {bar}")

    # Daily trend (if detailed)
    if detailed and "daily_trend" in stats:
        print(f"\n📅 每日查询趋势:")
        daily = stats["daily_trend"]
        for date, count in sorted(daily.items()):
            bar = "█" * (count // 10 + 1)
            print(f"   {date}: {count:4} {bar}")

    print("\n" + "=" * 60)


def export_stats(stats: dict[str, Any], output_file: str):
    """Export statistics to JSON file."""
    output_path = Path(output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"✅ 统计数据已导出到: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="查询分析工具 - 分析系统查询统计和性能"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=7,
        help="分析最近N天的数据 (默认: 7)"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="显示详细统计（包括每日趋势）"
    )
    parser.add_argument(
        "--export", "-e",
        type=str,
        metavar="FILE",
        help="导出统计数据到JSON文件"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出（不格式化）"
    )

    args = parser.parse_args()

    # Analyze queries
    stats = analyze_queries(days=args.days, detailed=args.detailed)

    # Output
    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print_stats(stats, detailed=args.detailed)

    # Export if requested
    if args.export:
        export_stats(stats, args.export)


if __name__ == "__main__":
    main()
