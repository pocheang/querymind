"""
Example usage of BatchChartExtractor demonstrating performance improvements.

This example shows how to use the batch chart extractor and compares
sequential vs concurrent processing times.
"""

import asyncio
import time
from pathlib import Path
from typing import List

from app.ingestion.utils.batch_chart_extractor import BatchChartExtractor
from app.ingestion.utils.chart_extractor import extract_chart_data_with_vision


async def example_batch_extraction():
    """Example: Extract charts from multiple images concurrently."""

    # Simulate having multiple chart images
    # In real usage, these would be actual image bytes from PDF pages
    sample_images = [
        b"chart_image_1",
        b"chart_image_2",
        b"chart_image_3",
        b"chart_image_4",
        b"chart_image_5",
    ]

    # Initialize batch extractor with batch_size=5 (default)
    extractor = BatchChartExtractor(batch_size=5)

    # Extract all charts concurrently
    results = await extractor.extract_charts_batch(
        images=sample_images,
        model="gpt-4o",
        api_key="your-api-key-here"
    )

    # Process results
    for idx, result in enumerate(results):
        if "error" in result:
            print(f"Chart {idx + 1} failed: {result['error']}")
        else:
            print(f"Chart {idx + 1}: {result.get('chart_type', 'unknown')} - {result.get('title', 'untitled')}")

    return results


async def compare_sequential_vs_concurrent():
    """Compare sequential vs concurrent processing times."""

    # Create test images
    num_images = 10
    test_images = [f"test_image_{i}".encode() for i in range(num_images)]

    print(f"\nProcessing {num_images} images...")
    print("=" * 60)

    # Simulate API delay (in real usage, this is the actual API call time)
    def mock_extract(image_bytes, model, api_key):
        time.sleep(0.2)  # Simulate 200ms API call
        return {
            "chart_type": "bar",
            "title": f"Chart {image_bytes.decode()}",
            "data": []
        }

    # Sequential processing
    print("\n1. Sequential Processing:")
    start = time.time()
    sequential_results = []
    for img in test_images:
        result = mock_extract(img, "gpt-4o", "test_key")
        sequential_results.append(result)
    sequential_time = time.time() - start
    print(f"   Time: {sequential_time:.2f}s")

    # Concurrent processing with batch_size=5
    print("\n2. Concurrent Processing (batch_size=5):")

    # Mock the actual extraction function
    import app.ingestion.utils.batch_chart_extractor as batch_module
    original_extract = batch_module.extract_chart_data_with_vision
    batch_module.extract_chart_data_with_vision = mock_extract

    try:
        extractor = BatchChartExtractor(batch_size=5)
        start = time.time()
        concurrent_results = await extractor.extract_charts_batch(
            test_images,
            model="gpt-4o",
            api_key="test_key"
        )
        concurrent_time = time.time() - start
        print(f"   Time: {concurrent_time:.2f}s")
    finally:
        # Restore original function
        batch_module.extract_chart_data_with_vision = original_extract

    # Calculate improvement
    print("\n" + "=" * 60)
    improvement = ((sequential_time - concurrent_time) / sequential_time) * 100
    print(f"Time Reduction: {improvement:.1f}%")
    print(f"Speedup: {sequential_time / concurrent_time:.2f}x")

    if improvement >= 40:
        print("✓ Target of 40% reduction achieved!")
    else:
        print(f"⚠ Target of 40% reduction not met (got {improvement:.1f}%)")


async def example_with_error_handling():
    """Example: Handle errors gracefully in batch processing."""

    print("\n\nExample: Error Handling")
    print("=" * 60)

    # Simulate mixed success/failure scenario
    test_images = [b"good_1", b"bad_image", b"good_2", b"good_3"]

    def mock_extract_with_errors(image_bytes, model, api_key):
        if b"bad" in image_bytes:
            raise ValueError("Invalid image format")
        return {"chart_type": "line", "title": "Success"}

    import app.ingestion.utils.batch_chart_extractor as batch_module
    original_extract = batch_module.extract_chart_data_with_vision
    batch_module.extract_chart_data_with_vision = mock_extract_with_errors

    try:
        extractor = BatchChartExtractor(batch_size=2)
        results = await extractor.extract_charts_batch(
            test_images,
            model="gpt-4o",
            api_key="test_key"
        )

        print(f"\nProcessed {len(results)} images:")
        success_count = sum(1 for r in results if "error" not in r)
        error_count = len(results) - success_count

        print(f"  ✓ Successful: {success_count}")
        print(f"  ✗ Failed: {error_count}")

        # Show error details
        for idx, result in enumerate(results):
            if "error" in result:
                print(f"\n  Image {idx + 1} error: {result['error']}")

    finally:
        batch_module.extract_chart_data_with_vision = original_extract


async def main():
    """Run all examples."""
    print("Batch Chart Extractor Examples")
    print("=" * 60)

    # Example 1: Performance comparison
    await compare_sequential_vs_concurrent()

    # Example 2: Error handling
    await example_with_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
