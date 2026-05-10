"""Chart and graph detection and extraction from PDFs."""

from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def detect_chart_in_image(image_bytes: bytes) -> Dict[str, any]:
    """
    Detect if image contains a chart/graph.

    Args:
        image_bytes: Image bytes

    Returns:
        Dict with detection results:
        - is_chart: bool
        - chart_type: str (bar, line, pie, scatter, etc.)
        - confidence: float
    """
    try:
        from PIL import Image
        from io import BytesIO

        img = Image.open(BytesIO(image_bytes))

        # Simple heuristics for chart detection
        # Real implementation would use ML model
        width, height = img.size

        # Charts are usually rectangular and not too small
        if width < 200 or height < 200:
            return {"is_chart": False, "chart_type": None, "confidence": 0.0}

        # Check aspect ratio (charts usually have reasonable aspect ratios)
        aspect_ratio = width / height
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            return {"is_chart": False, "chart_type": None, "confidence": 0.3}

        # Basic detection - assume it might be a chart
        # In production, use a trained model
        return {
            "is_chart": True,
            "chart_type": "unknown",
            "confidence": 0.6,
            "width": width,
            "height": height
        }

    except Exception as e:
        logger.error(f"Chart detection failed: {e}")
        return {"is_chart": False, "chart_type": None, "confidence": 0.0}


def extract_chart_data_with_vision(
    image_bytes: bytes,
    model: str = "gpt-4-vision",
    api_key: Optional[str] = None
) -> Dict[str, any]:
    """
    Extract data from chart using multimodal LLM.

    Args:
        image_bytes: Image bytes
        model: Model to use (gpt-4-vision, claude-3, etc.)
        api_key: API key for the model

    Returns:
        Dict with extracted data:
        - chart_type: str
        - title: str
        - data: list of dicts
        - description: str
    """
    try:
        if model.startswith("gpt-4"):
            return _extract_with_openai(image_bytes, api_key)
        elif model.startswith("claude"):
            return _extract_with_anthropic(image_bytes, api_key)
        else:
            return {"error": f"Unsupported model: {model}"}

    except Exception as e:
        logger.error(f"Chart extraction failed: {e}")
        return {"error": str(e)}


def _extract_with_openai(image_bytes: bytes, api_key: Optional[str]) -> Dict:
    """Extract chart data using OpenAI GPT-4V."""
    try:
        import base64
        from openai import OpenAI

        # Encode image
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        client = OpenAI(api_key=api_key)

        prompt = """Analyze this chart/graph and extract the data in structured format.

Please provide:
1. Chart type (bar, line, pie, scatter, etc.)
2. Chart title
3. Axis labels (if applicable)
4. Data points in JSON format
5. Brief description of what the chart shows

Format your response as JSON:
{
  "chart_type": "...",
  "title": "...",
  "x_label": "...",
  "y_label": "...",
  "data": [{"label": "...", "value": ...}, ...],
  "description": "..."
}"""

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )

        # Parse response
        content = response.choices[0].message.content

        # Try to extract JSON
        import json
        import re

        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return data
        else:
            return {"description": content, "raw_response": True}

    except ImportError:
        return {"error": "OpenAI library not installed"}
    except Exception as e:
        logger.error(f"OpenAI extraction failed: {e}")
        return {"error": str(e)}


def _extract_with_anthropic(image_bytes: bytes, api_key: Optional[str]) -> Dict:
    """Extract chart data using Anthropic Claude."""
    try:
        import base64
        from anthropic import Anthropic

        # Encode image
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        client = Anthropic(api_key=api_key)

        prompt = """Analyze this chart/graph and extract the data in structured format.

Please provide:
1. Chart type (bar, line, pie, scatter, etc.)
2. Chart title
3. Axis labels (if applicable)
4. Data points in JSON format
5. Brief description of what the chart shows

Format your response as JSON."""

        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        # Parse response
        content = message.content[0].text

        # Try to extract JSON
        import json
        import re

        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return data
        else:
            return {"description": content, "raw_response": True}

    except ImportError:
        return {"error": "Anthropic library not installed"}
    except Exception as e:
        logger.error(f"Anthropic extraction failed: {e}")
        return {"error": str(e)}


def chart_data_to_markdown(chart_data: Dict) -> str:
    """
    Convert extracted chart data to Markdown format.

    Args:
        chart_data: Extracted chart data

    Returns:
        Markdown formatted text
    """
    if "error" in chart_data:
        return f"[Chart extraction error: {chart_data['error']}]"

    lines = []

    # Title
    if chart_data.get("title"):
        lines.append(f"## {chart_data['title']}")
        lines.append("")

    # Chart type
    if chart_data.get("chart_type"):
        lines.append(f"**Chart Type**: {chart_data['chart_type']}")
        lines.append("")

    # Description
    if chart_data.get("description"):
        lines.append(chart_data["description"])
        lines.append("")

    # Data table
    if chart_data.get("data"):
        lines.append("### Data")
        lines.append("")

        data = chart_data["data"]
        if isinstance(data, list) and len(data) > 0:
            # Create table
            if isinstance(data[0], dict):
                # Get keys
                keys = list(data[0].keys())
                # Header
                lines.append("| " + " | ".join(keys) + " |")
                lines.append("| " + " | ".join(["---"] * len(keys)) + " |")
                # Rows
                for row in data:
                    values = [str(row.get(k, "")) for k in keys]
                    lines.append("| " + " | ".join(values) + " |")
            else:
                # Simple list
                for item in data:
                    lines.append(f"- {item}")

    return "\n".join(lines)
