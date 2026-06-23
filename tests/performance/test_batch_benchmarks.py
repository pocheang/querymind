"""Test script for batch chart extraction benchmarks."""

import sys
from pathlib import Path

# Add tests/performance to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from benchmark_pdf_processing import print_summary, run_batch_chart_extraction_benchmark, run_batch_size_comparison


def test_basic_batch_benchmark():
    """Test basic batch chart extraction benchmark."""
    print("\n" + "=" * 60)
    print("Test 1: Basic Batch Chart Extraction Benchmark")
    print("=" * 60)

    result = run_batch_chart_extraction_benchmark(num_images=10, batch_size=5, mock_api_delay=0.1)

    print_summary([result])

    # Verify results
    assert result["operation"] == "chart_extraction_comparison"
    assert result["num_images"] == 10
    assert result["batch_size"] == 5
    assert "speedup_factor" in result
    assert "time_saved_percent" in result
    assert result["speedup_factor"] > 1.0, "Batch should be faster than sequential"

    print("\n✓ Basic benchmark test passed")
    return result


def test_batch_size_comparison():
    """Test comparison across different batch sizes."""
    print("\n" + "=" * 60)
    print("Test 2: Batch Size Comparison")
    print("=" * 60)

    results = run_batch_size_comparison(num_images=20, batch_sizes=[5, 10, 20], mock_api_delay=0.1)

    print_summary(results)

    # Verify results
    assert len(results) == 3
    for result in results:
        assert result["operation"] == "chart_extraction_comparison"
        assert result["speedup_factor"] > 1.0

    # Print comparison table
    print("\n" + "=" * 60)
    print("Batch Size Performance Comparison")
    print("=" * 60)
    print(f"{'Batch Size':<12} {'Speedup':<10} {'Time Saved':<15} {'Meets Target':<15}")
    print("-" * 60)

    for result in results:
        batch_size = result["batch_size"]
        speedup = f"{result['speedup_factor']}x"
        time_saved = f"{result['time_saved_percent']}%"
        meets_target = "✓ Yes" if result["meets_40_percent_target"] else "✗ No"
        print(f"{batch_size:<12} {speedup:<10} {time_saved:<15} {meets_target:<15}")

    print("\n✓ Batch size comparison test passed")
    return results


def test_40_percent_improvement():
    """Test that batch processing achieves 40% improvement."""
    print("\n" + "=" * 60)
    print("Test 3: Verify 40% Improvement Target")
    print("=" * 60)

    result = run_batch_chart_extraction_benchmark(num_images=20, batch_size=10, mock_api_delay=0.1)

    speedup = result["speedup_factor"]
    time_saved_percent = result["time_saved_percent"]
    meets_target = result["meets_40_percent_target"]

    print("\nResults:")
    print(f"  Speedup Factor: {speedup}x")
    print(f"  Time Saved: {time_saved_percent}%")
    print(f"  Target (40% = 1.67x speedup): {'✓ PASS' if meets_target else '✗ FAIL'}")

    if meets_target:
        print("\n✓ Successfully achieved 40%+ improvement!")
    else:
        print("\n✗ Did not meet 40% improvement target")
        print("  Expected: >= 1.67x speedup")
        print(f"  Actual: {speedup}x speedup")

    assert meets_target, f"Expected >= 1.67x speedup, got {speedup}x"

    print("\n✓ 40% improvement test passed")
    return result


def main():
    """Run all benchmark tests."""
    print("\n" + "=" * 60)
    print("BATCH CHART EXTRACTION BENCHMARK TESTS")
    print("=" * 60)

    try:
        # Test 1: Basic benchmark
        test_basic_batch_benchmark()

        # Test 2: Batch size comparison
        test_batch_size_comparison()

        # Test 3: 40% improvement verification
        test_40_percent_improvement()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nBatch chart extraction benchmarks are working correctly!")
        print("Performance improvement target (40%) is being met.")

        return 0

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
