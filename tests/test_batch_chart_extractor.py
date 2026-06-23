"""Tests for batch chart extraction with async concurrency."""

from unittest.mock import patch

import pytest

from app.ingestion.utils.batch_chart_extractor import BatchChartExtractor, extract_charts_batch_simple


@pytest.fixture
def sample_images():
    """Create sample image bytes for testing."""
    return [
        b"fake_image_1",
        b"fake_image_2",
        b"fake_image_3",
        b"fake_image_4",
        b"fake_image_5",
    ]


@pytest.fixture
def mock_chart_data():
    """Mock chart extraction result."""
    return {
        "chart_type": "bar",
        "title": "Test Chart",
        "data": [{"label": "A", "value": 10}],
        "description": "A test chart",
    }


@pytest.mark.asyncio
async def test_batch_extractor_basic(sample_images, mock_chart_data):
    """Test basic batch extraction functionality."""
    extractor = BatchChartExtractor(batch_size=2)

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.return_value = mock_chart_data

        results = await extractor.extract_charts_batch(sample_images, model="gpt-4o", api_key="test_key")

    assert len(results) == 5
    assert all("error" not in r for r in results)
    assert all(r["chart_type"] == "bar" for r in results)


@pytest.mark.asyncio
async def test_batch_extractor_empty_list():
    """Test with empty image list."""
    extractor = BatchChartExtractor(batch_size=5)

    results = await extractor.extract_charts_batch([], model="gpt-4o", api_key="test_key")

    assert results == []


@pytest.mark.asyncio
async def test_batch_extractor_with_errors(sample_images):
    """Test error handling in batch extraction."""
    extractor = BatchChartExtractor(batch_size=2)

    def mock_extract_with_error(image_bytes, model, api_key):
        if image_bytes == b"fake_image_3":
            raise ValueError("Extraction failed")
        return {"chart_type": "line", "title": "Success"}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = mock_extract_with_error

        results = await extractor.extract_charts_batch(sample_images, model="gpt-4o", api_key="test_key")

    assert len(results) == 5

    # Check that one result has an error
    error_results = [r for r in results if "error" in r]
    success_results = [r for r in results if "error" not in r]

    assert len(error_results) == 1
    assert len(success_results) == 4
    assert "Extraction failed" in error_results[0]["error"]


@pytest.mark.asyncio
async def test_batch_size_configuration():
    """Test that batch size is respected."""
    images = [b"img" + str(i).encode() for i in range(10)]
    extractor = BatchChartExtractor(batch_size=3)

    call_batches = []

    def track_calls(image_bytes, model, api_key):
        call_batches.append(image_bytes)
        return {"chart_type": "test"}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = track_calls

        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")

    assert len(results) == 10
    # All images should have been processed
    assert len(call_batches) == 10


@pytest.mark.asyncio
async def test_convenience_function(sample_images, mock_chart_data):
    """Test the convenience function."""
    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.return_value = mock_chart_data

        results = await extract_charts_batch_simple(
            sample_images, model="claude-3-5-sonnet", api_key="test_key", batch_size=3
        )

    assert len(results) == 5
    assert all(r["chart_type"] == "bar" for r in results)


@pytest.mark.asyncio
async def test_concurrent_execution_speed():
    """Test that concurrent execution is faster than sequential."""
    import time

    images = [b"img" + str(i).encode() for i in range(10)]

    def slow_extract(image_bytes, model, api_key):
        time.sleep(0.1)  # Simulate API delay
        return {"chart_type": "test"}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = slow_extract

        extractor = BatchChartExtractor(batch_size=5)

        start = time.time()
        results = await extractor.extract_charts_batch(images, model="gpt-4o", api_key="test_key")
        duration = time.time() - start

    # With batch_size=5, 10 images should take ~0.2s (2 batches)
    # Sequential would take ~1.0s (10 * 0.1s)
    # Allow some overhead, but should be significantly faster
    assert duration < 0.5, f"Concurrent execution took {duration}s, expected < 0.5s"
    assert len(results) == 10


@pytest.mark.asyncio
async def test_different_models(sample_images):
    """Test with different model types."""
    extractor = BatchChartExtractor(batch_size=5)

    models_to_test = ["gpt-4o", "gpt-4-turbo", "claude-3-5-sonnet"]

    for model in models_to_test:
        with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
            mock_extract.return_value = {"chart_type": "test", "model_used": model}

            results = await extractor.extract_charts_batch(
                sample_images[:2],  # Just test with 2 images
                model=model,
                api_key="test_key",
            )

        assert len(results) == 2
        assert all(r["model_used"] == model for r in results)


@pytest.mark.asyncio
async def test_exception_types_captured(sample_images):
    """Test that different exception types are properly captured."""
    extractor = BatchChartExtractor(batch_size=5)

    def raise_different_errors(image_bytes, model, api_key):
        if image_bytes == b"fake_image_1":
            raise ValueError("Value error")
        elif image_bytes == b"fake_image_2":
            raise RuntimeError("Runtime error")
        elif image_bytes == b"fake_image_3":
            raise ConnectionError("Connection error")
        return {"chart_type": "success"}

    with patch("app.ingestion.utils.batch_chart_extractor.extract_chart_data_with_vision") as mock_extract:
        mock_extract.side_effect = raise_different_errors

        results = await extractor.extract_charts_batch(sample_images, model="gpt-4o", api_key="test_key")

    assert len(results) == 5

    error_results = [r for r in results if "error" in r]
    assert len(error_results) == 3

    # Check error types are captured
    error_types = [r.get("error_type") for r in error_results]
    assert "ValueError" in error_types
    assert "RuntimeError" in error_types
    assert "ConnectionError" in error_types
