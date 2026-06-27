"""Integration tests for batch chart extraction.

Tests end-to-end batch processing with real image data, concurrent execution,
error recovery, and performance verification.
"""

import time
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw

from app.ingestion.utils.batch_chart_extractor import BatchChartExtractor, extract_charts_batch_simple


def create_test_chart_image(chart_type: str = "bar", width: int = 400, height: int = 300) -> bytes:
    """Create a real test chart image using PIL.

    Args:
        chart_type: Type of chart to create (bar, line, pie)
        width: Image width
        height: Image height

    Returns:
        Image bytes in PNG format
    """
    # Create a new image with white background
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Draw a simple chart based on type
    if chart_type == "bar":
        # Draw simple bar chart
        bar_width = 60
        bar_spacing = 20
        colors = ["red", "blue", "green", "orange"]
        heights = [150, 200, 120, 180]

        for i, (color, bar_height) in enumerate(zip(colors, heights, strict=False)):
            x = 50 + i * (bar_width + bar_spacing)
            y = height - 50 - bar_height
            draw.rectangle([x, y, x + bar_width, height - 50], fill=color)

    elif chart_type == "line":
        # Draw simple line chart
        points = [(50, 200), (150, 150), (250, 180), (350, 100)]
        draw.line(points, fill="blue", width=3)
        for point in points:
            draw.ellipse([point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5], fill="red")

    elif chart_type == "pie":
        # Draw simple pie chart
        center_x, center_y = width // 2, height // 2
        radius = 100
        draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            fill="lightblue",
            outline="black",
        )
        draw.pieslice(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius], start=0, end=120, fill="red"
        )
        draw.pieslice(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            start=120,
            end=240,
            fill="green",
        )

    # Add title
    draw.text((width // 2 - 50, 20), f"{chart_type.upper()} Chart", fill="black")

    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_with_real_images():
    """Test batch extraction with actual image data (not mocked).

    Verifies that the batch extractor can process real PNG images
    and handle the full extraction pipeline.
    """
    # Create real test images
    images = [
        create_test_chart_image("bar"),
        create_test_chart_image("line"),
        create_test_chart_image("pie"),
        create_test_chart_image("bar"),
        create_test_chart_image("line"),
    ]

    # Verify images are valid
    for img_bytes in images:
        assert len(img_bytes) > 0
        # Verify it's a valid PNG
        img = Image.open(BytesIO(img_bytes))
        assert img.format == "PNG"

    # Mock the API call but test real async execution
    mock_chart_data = {
        "chart_type": "bar",
        "title": "Test Chart",
        "data": [{"label": "A", "value": 10}],
        "description": "A test chart",
    }

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.return_value = mock_chart_data

        extractor = BatchChartExtractor(batch_size=3)
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")

    # Verify results
    assert len(results) == 5
    assert all("error" not in r for r in results)
    assert all(r["chart_type"] == "bar" for r in results)

    # Verify all images were processed
    assert mock_extract.call_count == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_performance():
    """Test that concurrent execution is faster than sequential.

    Verifies that batch processing with concurrency provides
    measurable performance improvement over sequential processing.
    """
    # Create 15 real test images
    images = [create_test_chart_image("bar") for _ in range(15)]

    def slow_extract(image_bytes, model, api_key):
        """Simulate slow API call."""
        time.sleep(0.1)  # 100ms per call
        return {"chart_type": "test", "title": "Chart"}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = slow_extract

        # Test with batch_size=5 (concurrent)
        extractor = BatchChartExtractor(batch_size=5)

        start_time = time.time()
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")
        concurrent_duration = time.time() - start_time

    # Verify results
    assert len(results) == 15
    assert all("error" not in r for r in results)

    # Performance verification:
    # - Sequential would take: 15 * 0.1 = 1.5 seconds
    # - Concurrent (batch_size=5) should take: 3 batches * 0.1 = ~0.3 seconds
    # - Allow overhead, but should be significantly faster than sequential

    # Concurrent should be at least 2x faster than sequential
    sequential_estimate = 15 * 0.1  # 1.5 seconds
    assert concurrent_duration < sequential_estimate / 2, (
        f"Concurrent ({concurrent_duration:.2f}s) not faster than sequential (~{sequential_estimate}s)"
    )

    # Should complete in reasonable time (< 1 second with overhead)
    assert concurrent_duration < 1.0, f"Concurrent execution took {concurrent_duration:.2f}s, expected < 1.0s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_with_mixed_results():
    """Test batch extraction with some successes and some failures.

    Verifies that the system handles mixed results correctly,
    continuing to process successful images even when some fail.
    """
    # Create real test images
    images = [
        create_test_chart_image("bar"),
        create_test_chart_image("line"),
        create_test_chart_image("pie"),
        create_test_chart_image("bar"),
        create_test_chart_image("line"),
        create_test_chart_image("pie"),
    ]

    call_count = [0]

    def mixed_results(image_bytes, model, api_key):
        """Return success for some, failure for others."""
        call_count[0] += 1
        # Fail on images 2 and 5 (indices 1 and 4)
        if call_count[0] in [2, 5]:
            raise ValueError(f"Extraction failed for image {call_count[0]}")
        return {"chart_type": "success", "title": f"Chart {call_count[0]}", "data": []}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = mixed_results

        extractor = BatchChartExtractor(batch_size=3)
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")

    # Verify all images were processed
    assert len(results) == 6

    # Check success and error counts
    success_results = [r for r in results if "error" not in r]
    error_results = [r for r in results if "error" in r]

    assert len(success_results) == 4
    assert len(error_results) == 2

    # Verify error details
    for error_result in error_results:
        assert "Extraction failed" in error_result["error"]
        assert error_result["error_type"] == "ValueError"

    # Verify success results
    for success_result in success_results:
        assert success_result["chart_type"] == "success"
        assert "Chart" in success_result["title"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_with_large_batch():
    """Test batch extraction with large number of images (20+).

    Verifies that the system can handle large batches efficiently
    and maintains stability with many concurrent operations.
    """
    # Create 25 real test images
    images = [create_test_chart_image(chart_type) for chart_type in ["bar", "line", "pie"] * 8 + ["bar"]]

    assert len(images) == 25

    call_count = [0]

    def track_calls(image_bytes, model, api_key):
        """Track calls and return mock data."""
        call_count[0] += 1
        return {"chart_type": "test", "title": f"Chart {call_count[0]}", "data": [{"value": call_count[0]}]}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = track_calls

        extractor = BatchChartExtractor(batch_size=5)

        start_time = time.time()
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")
        duration = time.time() - start_time

    # Verify all images were processed
    assert len(results) == 25
    assert call_count[0] == 25

    # Verify no errors
    assert all("error" not in r for r in results)

    # Concurrent execution may change mock call order, but we should still
    # receive a complete, deduplicated result set.
    observed_values = sorted(result["data"][0]["value"] for result in results)
    assert observed_values == list(range(1, 26))
    assert {result["title"] for result in results} == {f"Chart {i}" for i in range(1, 26)}

    # Performance check: should complete in reasonable time
    # 25 images / 5 batch_size = 5 batches
    # Should complete quickly with mocked calls
    assert duration < 2.0, f"Large batch took {duration:.2f}s, expected < 2.0s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_error_recovery():
    """Test that one failure doesn't stop processing of other images.

    Verifies robust error recovery where failures are isolated
    and don't affect processing of other images in the batch.
    """
    # Create real test images
    images = [create_test_chart_image("bar") for _ in range(10)]

    call_count = [0]

    def intermittent_failures(image_bytes, model, api_key):
        """Fail on specific images but succeed on others."""
        call_count[0] += 1
        # Fail on images 3, 6, and 9
        if call_count[0] in [3, 6, 9]:
            raise ConnectionError(f"Network error for image {call_count[0]}")
        return {"chart_type": "bar", "title": f"Success {call_count[0]}", "data": []}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = intermittent_failures

        extractor = BatchChartExtractor(batch_size=4)
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")

    # Verify all images were attempted
    assert len(results) == 10
    assert call_count[0] == 10

    # Check error distribution
    success_results = [r for r in results if "error" not in r]
    error_results = [r for r in results if "error" in r]

    assert len(success_results) == 7
    assert len(error_results) == 3

    # Concurrent execution can reshuffle which input hits a given mocked
    # failure slot, so verify the aggregate error handling instead of index positions.
    for error_result in error_results:
        assert "Network error" in error_result["error"]
        assert error_result["error_type"] == "ConnectionError"

    for success_result in success_results:
        assert success_result["chart_type"] == "bar"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_with_different_models():
    """Test batch extraction with OpenAI and Anthropic models.

    Verifies that the batch extractor works correctly with
    different model providers and configurations.
    """
    # Create real test images
    images = [
        create_test_chart_image("bar"),
        create_test_chart_image("line"),
        create_test_chart_image("pie"),
    ]

    models_to_test = [
        ("gpt-4o", "openai"),
        ("gpt-4-turbo", "openai"),
        ("claude-3-5-sonnet-20241022", "anthropic"),
        ("claude-3-opus-20240229", "anthropic"),
    ]

    for model, provider in models_to_test:
        call_count = [0]

        def model_specific_response(image_bytes, model_name, api_key):
            """Return model-specific response."""
            call_count[0] += 1
            return {
                "chart_type": "test",
                "title": f"Chart from {provider}",
                "model": model_name,
                "provider": provider,
                "image_num": call_count[0],
            }

        with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
            mock_extract.side_effect = model_specific_response

            extractor = BatchChartExtractor(batch_size=2)
            results = await extractor.extract_charts_batch(images, model=model, api_key=f"test_key_{provider}")

        # Verify results for this model
        assert len(results) == 3
        assert call_count[0] == 3

        # Verify all results are from the correct model
        for result in results:
            assert "error" not in result
            assert result["model"] == model
            assert result["provider"] == provider
            assert provider in result["title"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_convenience_function():
    """Test the convenience function with real images.

    Verifies that the simple wrapper function works correctly
    for end-to-end batch extraction.
    """
    # Create real test images
    images = [
        create_test_chart_image("bar"),
        create_test_chart_image("line"),
        create_test_chart_image("pie"),
        create_test_chart_image("bar"),
    ]

    mock_data = {"chart_type": "mixed", "title": "Test Chart", "data": []}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.return_value = mock_data

        # Use convenience function
        results = await extract_charts_batch_simple(
            images, model="claude-3-5-sonnet-20241022", api_key="test_key", batch_size=2
        )

    # Verify results
    assert len(results) == 4
    assert all("error" not in r for r in results)
    assert all(r["chart_type"] == "mixed" for r in results)
    assert mock_extract.call_count == 4


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_with_timeout_errors():
    """Test batch extraction with timeout errors.

    Verifies that timeout errors are handled gracefully
    and don't block other image processing.
    """
    # Create real test images
    images = [create_test_chart_image("bar") for _ in range(8)]

    call_count = [0]

    def timeout_on_some(image_bytes, model, api_key):
        """Timeout on specific images."""
        call_count[0] += 1
        if call_count[0] in [2, 5, 7]:
            raise TimeoutError(f"Request timeout for image {call_count[0]}")
        return {"chart_type": "bar", "title": f"Chart {call_count[0]}", "data": []}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = timeout_on_some

        extractor = BatchChartExtractor(batch_size=3)
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")

    # Verify all images were attempted
    assert len(results) == 8

    # Check error handling
    error_results = [r for r in results if "error" in r]
    success_results = [r for r in results if "error" not in r]

    assert len(error_results) == 3
    assert len(success_results) == 5

    # Verify timeout errors
    for error_result in error_results:
        assert "timeout" in error_result["error"].lower()
        assert error_result["error_type"] == "TimeoutError"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_extraction_empty_and_edge_cases():
    """Test batch extraction with edge cases.

    Verifies handling of empty lists, single images,
    and other boundary conditions.
    """
    extractor = BatchChartExtractor(batch_size=5)

    # Test 1: Empty list
    results = await extractor.extract_charts_batch([], model="gpt-4o", api_key="test_key")
    assert results == []

    # Test 2: Single image
    single_image = [create_test_chart_image("bar")]

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.return_value = {"chart_type": "bar", "title": "Single"}

        results = await extractor.extract_charts_batch(single_image, model="gpt-4o", api_key="test_key")

    assert len(results) == 1
    assert results[0]["chart_type"] == "bar"

    # Test 3: Batch size larger than image count
    images = [create_test_chart_image("bar") for _ in range(3)]

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.return_value = {"chart_type": "bar", "title": "Test"}

        extractor_large = BatchChartExtractor(batch_size=10)
        results = await extractor_large.extract_charts_batch(images, model="gpt-4o", api_key="test_key")

    assert len(results) == 3
    assert all("error" not in r for r in results)

