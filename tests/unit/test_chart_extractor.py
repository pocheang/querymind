"""Unit tests for chart extraction utilities."""

from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from app.ingestion.utils.chart_extractor import (
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_SIZE_BYTES,
    _extract_json_from_text,
    _resize_image_if_needed,
    chart_data_to_markdown,
    detect_chart_in_image,
    extract_chart_data_with_vision,
)

# Fixtures for test images


@pytest.fixture
def small_image_bytes():
    """Create a small image (under 5MB)."""
    img = Image.new("RGB", (800, 600), color="white")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def large_image_bytes():
    """Create a large image (over 5MB)."""
    # Create a large high-resolution image with high quality to exceed 5MB
    img = Image.new("RGB", (6000, 4500), color="blue")
    # Add some noise to make it less compressible
    import random

    pixels = img.load()
    for i in range(0, img.width, 10):
        for j in range(0, img.height, 10):
            pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    buffer = BytesIO()
    img.save(buffer, format="PNG")  # PNG is less compressed, will be larger
    return buffer.getvalue()


@pytest.fixture
def chart_like_image_bytes():
    """Create an image with chart-like dimensions."""
    img = Image.new("RGB", (1200, 800), color="white")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def tiny_image_bytes():
    """Create a tiny image (too small to be a chart)."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def wide_image_bytes():
    """Create an image with extreme aspect ratio."""
    img = Image.new("RGB", (2000, 400), color="green")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


# Image resizing tests


def test_resize_small_image_unchanged(small_image_bytes):
    """Test that small images are not resized."""
    original_size = len(small_image_bytes)
    result = _resize_image_if_needed(small_image_bytes)

    assert len(result) == original_size
    assert result == small_image_bytes


def test_resize_large_image(large_image_bytes):
    """Test that large images are resized to fit 5MB limit."""
    original_size = len(large_image_bytes)

    # If the fixture didn't create a large enough image, create one here
    if original_size <= MAX_IMAGE_SIZE_BYTES:
        # Create a guaranteed large image by using uncompressed BMP format
        img = Image.new("RGB", (8000, 6000), color="blue")
        import random

        pixels = img.load()
        for i in range(0, img.width, 5):
            for j in range(0, img.height, 5):
                pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        buffer = BytesIO()
        img.save(buffer, format="BMP")  # BMP is uncompressed, will be very large
        large_image_bytes = buffer.getvalue()
        original_size = len(large_image_bytes)

    # Ensure we have a large image
    assert original_size > MAX_IMAGE_SIZE_BYTES, (
        f"Test image is only {original_size} bytes, need > {MAX_IMAGE_SIZE_BYTES}"
    )

    result = _resize_image_if_needed(large_image_bytes)

    # Should be smaller than original
    assert len(result) < original_size
    # Should be under the limit
    assert len(result) <= MAX_IMAGE_SIZE_BYTES

    # Verify it's still a valid image
    img = Image.open(BytesIO(result))
    assert img.format == "JPEG"


def test_resize_preserves_aspect_ratio(large_image_bytes):
    """Test that resizing preserves aspect ratio."""
    # Get original dimensions
    original_img = Image.open(BytesIO(large_image_bytes))
    original_aspect = original_img.width / original_img.height

    # Resize
    result = _resize_image_if_needed(large_image_bytes)

    # Check new dimensions
    resized_img = Image.open(BytesIO(result))
    new_aspect = resized_img.width / resized_img.height

    # Aspect ratio should be approximately the same (within 1%)
    assert abs(original_aspect - new_aspect) / original_aspect < 0.01


def test_resize_respects_max_dimension():
    """Test that resizing respects MAX_IMAGE_DIMENSION."""
    # Create an extremely large image that will exceed both size and dimension limits
    img = Image.new("RGB", (5000, 5000), color="yellow")
    # Add noise to make it less compressible and exceed 5MB
    import random

    pixels = img.load()
    for i in range(0, img.width, 10):
        for j in range(0, img.height, 10):
            pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    large_bytes = buffer.getvalue()

    # Only test if the image is actually large enough to trigger resizing
    if len(large_bytes) > MAX_IMAGE_SIZE_BYTES:
        result = _resize_image_if_needed(large_bytes)

        # Check dimensions don't exceed maximum
        resized_img = Image.open(BytesIO(result))
        assert resized_img.width <= MAX_IMAGE_DIMENSION
        assert resized_img.height <= MAX_IMAGE_DIMENSION


def test_resize_handles_corrupt_image():
    """Test that resize handles corrupt image data gracefully."""
    corrupt_bytes = b"not an image"

    # Should return original bytes on error
    result = _resize_image_if_needed(corrupt_bytes)
    assert result == corrupt_bytes


# Chart detection tests


def test_detect_chart_reasonable_size(chart_like_image_bytes):
    """Test detection of reasonably-sized images."""
    result = detect_chart_in_image(chart_like_image_bytes)

    assert result["is_chart"] is True
    assert result["confidence"] > 0.5
    assert "width" in result
    assert "height" in result
    assert result["width"] == 1200
    assert result["height"] == 800


def test_detect_chart_too_small(tiny_image_bytes):
    """Test that too-small images are rejected."""
    result = detect_chart_in_image(tiny_image_bytes)

    assert result["is_chart"] is False
    assert result["chart_type"] is None
    assert result["confidence"] == 0.0


def test_detect_chart_bad_aspect_ratio(wide_image_bytes):
    """Test that images with extreme aspect ratios are flagged."""
    result = detect_chart_in_image(wide_image_bytes)

    # Wide image has aspect ratio 2000/400 = 5.0, which exceeds 3.0
    assert result["is_chart"] is False
    assert result["confidence"] < 0.5


def test_detect_chart_narrow_image():
    """Test detection of very narrow images."""
    # Create a tall narrow image (aspect ratio < 0.3)
    img = Image.new("RGB", (300, 1500), color="purple")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    narrow_bytes = buffer.getvalue()

    result = detect_chart_in_image(narrow_bytes)

    # Aspect ratio is 300/1500 = 0.2, which is < 0.3
    assert result["is_chart"] is False


def test_detect_chart_handles_corrupt_image():
    """Test that detection handles corrupt images gracefully."""
    corrupt_bytes = b"invalid image data"

    result = detect_chart_in_image(corrupt_bytes)

    assert result["is_chart"] is False
    assert result["chart_type"] is None
    assert result["confidence"] == 0.0


# Vision API error handling tests


def test_extract_missing_api_key(chart_like_image_bytes):
    """Test handling of missing API key."""
    result = extract_chart_data_with_vision(chart_like_image_bytes, model="gpt-4o", api_key=None)

    assert "error" in result
    assert "API key" in result["error"]


def test_extract_unsupported_model(chart_like_image_bytes):
    """Test handling of unsupported model."""
    result = extract_chart_data_with_vision(chart_like_image_bytes, model="unsupported-model-xyz", api_key="fake-key")

    assert "error" in result
    assert "Unsupported model" in result["error"]


@patch("app.ingestion.utils.chart_extractor._extract_with_openai")
def test_extract_openai_network_error(mock_extract, chart_like_image_bytes):
    """Test handling of OpenAI network errors."""
    # Mock the extraction function to raise an exception
    mock_extract.side_effect = Exception("Network error")

    result = extract_chart_data_with_vision(chart_like_image_bytes, model="gpt-4o", api_key="test-key")

    assert "error" in result
    assert "Network error" in result["error"]


@patch("app.ingestion.utils.chart_extractor._extract_with_anthropic")
def test_extract_anthropic_network_error(mock_extract, chart_like_image_bytes):
    """Test handling of Anthropic network errors."""
    # Mock the extraction function to raise an exception
    mock_extract.side_effect = Exception("API timeout")

    result = extract_chart_data_with_vision(
        chart_like_image_bytes, model="claude-3-5-sonnet-20241022", api_key="test-key"
    )

    assert "error" in result
    assert "API timeout" in result["error"]


@patch("app.ingestion.utils.chart_extractor._extract_with_openai")
def test_extract_openai_success(mock_extract, chart_like_image_bytes):
    """Test successful OpenAI extraction."""
    # Mock successful response
    mock_extract.return_value = {
        "chart_type": "bar",
        "title": "Sales Data",
        "data": [{"label": "Q1", "value": 100}],
        "description": "Quarterly sales",
    }

    result = extract_chart_data_with_vision(chart_like_image_bytes, model="gpt-4o", api_key="test-key")

    assert "error" not in result
    assert result["chart_type"] == "bar"
    assert result["title"] == "Sales Data"
    assert len(result["data"]) == 1


@patch("app.ingestion.utils.chart_extractor._extract_with_anthropic")
def test_extract_anthropic_success(mock_extract, chart_like_image_bytes):
    """Test successful Anthropic extraction."""
    # Mock successful response
    mock_extract.return_value = {
        "chart_type": "line",
        "title": "Temperature Trends",
        "data": [{"month": "Jan", "temp": 20}],
        "description": "Monthly temperatures",
    }

    result = extract_chart_data_with_vision(
        chart_like_image_bytes, model="claude-3-5-sonnet-20241022", api_key="test-key"
    )

    assert "error" not in result
    assert result["chart_type"] == "line"
    assert result["title"] == "Temperature Trends"


# JSON extraction tests


def test_extract_json_from_code_block():
    """Test extracting JSON from markdown code block."""
    text = """Here is the data:
```json
{"chart_type": "bar", "title": "Test"}
```
Some other text."""

    result = _extract_json_from_text(text)

    assert result is not None
    assert result["chart_type"] == "bar"
    assert result["title"] == "Test"


def test_extract_json_from_plain_text():
    """Test extracting JSON from plain text."""
    text = 'Some text before {"chart_type": "pie", "value": 42} and after'

    result = _extract_json_from_text(text)

    assert result is not None
    assert result["chart_type"] == "pie"
    assert result["value"] == 42


def test_extract_json_nested_objects():
    """Test extracting nested JSON objects."""
    text = """{"outer": {"inner": {"value": 123}}, "other": "data"}"""

    result = _extract_json_from_text(text)

    assert result is not None
    assert result["outer"]["inner"]["value"] == 123
    assert result["other"] == "data"


def test_extract_json_no_json():
    """Test handling text with no JSON."""
    text = "This is just plain text with no JSON at all."

    result = _extract_json_from_text(text)

    assert result is None


def test_extract_json_invalid_json():
    """Test handling invalid JSON."""
    text = '{"invalid": json, "missing": quotes}'

    result = _extract_json_from_text(text)

    assert result is None


# Markdown conversion tests


def test_chart_data_to_markdown_full():
    """Test converting complete chart data to markdown."""
    chart_data = {
        "chart_type": "bar",
        "title": "Sales Report",
        "description": "Q1 sales by region",
        "data": [{"region": "North", "sales": 1000}, {"region": "South", "sales": 1500}],
    }

    markdown = chart_data_to_markdown(chart_data)

    assert "## Sales Report" in markdown
    assert "**Chart Type**: bar" in markdown
    assert "Q1 sales by region" in markdown
    assert "| region | sales |" in markdown
    assert "| North | 1000 |" in markdown
    assert "| South | 1500 |" in markdown


def test_chart_data_to_markdown_error():
    """Test converting error result to markdown."""
    chart_data = {"error": "API key not configured"}

    markdown = chart_data_to_markdown(chart_data)

    assert "[Chart extraction error: API key not configured]" in markdown


def test_chart_data_to_markdown_minimal():
    """Test converting minimal chart data."""
    chart_data = {"description": "Simple chart"}

    markdown = chart_data_to_markdown(chart_data)

    assert "Simple chart" in markdown


def test_chart_data_to_markdown_list_data():
    """Test converting chart data with simple list."""
    chart_data = {"title": "Categories", "data": ["Category A", "Category B", "Category C"]}

    markdown = chart_data_to_markdown(chart_data)

    assert "## Categories" in markdown
    assert "- Category A" in markdown
    assert "- Category B" in markdown
    assert "- Category C" in markdown


def test_chart_data_to_markdown_empty_data():
    """Test converting chart data with empty data field."""
    chart_data = {"title": "Empty Chart", "data": []}

    markdown = chart_data_to_markdown(chart_data)

    assert "## Empty Chart" in markdown
    # Should not crash, just skip the data section
