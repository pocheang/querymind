import sys
from types import SimpleNamespace

from app.ingestion.utils.chart_extractor import _extract_with_anthropic, _extract_with_openai
from app.ingestion.utils.vision_utils import _describe_image_openai


def test_describe_image_openai_preserves_inline_image_data(monkeypatch):
    seen = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "caption"}}]}

    class Client:
        def __init__(self, timeout):
            seen["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json):
            seen["url"] = url
            seen["headers"] = headers
            seen["json"] = json
            return Response()

    monkeypatch.setattr("app.ingestion.utils.vision_utils.httpx.Client", Client)

    settings = SimpleNamespace(
        openai_api_key="sk-test",
        openai_base_url="https://api.openai.com",
        openai_vision_model="gpt-4.1-mini",
        openai_chat_model="gpt-4.1-mini",
    )

    result = _describe_image_openai(b"\x89PNG", settings)

    assert result["status"] == "ok"
    image_url = seen["json"]["messages"][1]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")


def test_describe_image_openai_handles_unexpected_response_shape_without_name_error(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {}}]}

    class Client:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers, json):
            return Response()

    monkeypatch.setattr("app.ingestion.utils.vision_utils.httpx.Client", Client)

    settings = SimpleNamespace(
        openai_api_key="sk-test",
        openai_base_url="https://api.openai.com",
        openai_vision_model="gpt-4.1-mini",
        openai_chat_model="gpt-4.1-mini",
    )

    result = _describe_image_openai(b"\x89PNG", settings)

    assert result["status"] == "openai_empty"


def test_chart_extractor_openai_preserves_inline_image_data(monkeypatch):
    seen = {}

    class FakeCompletions:
        def create(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"chart_type":"bar"}'))]
            )

    class FakeOpenAI:
        def __init__(self, api_key):
            seen["api_key"] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_module = SimpleNamespace(OpenAI=FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    result = _extract_with_openai(b"img", api_key="sk-test", model="gpt-4o")

    assert result["chart_type"] == "bar"
    image_url = seen["messages"][0]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/jpeg;base64,")


def test_chart_extractor_anthropic_preserves_inline_base64_data(monkeypatch):
    seen = {}

    class FakeMessages:
        def create(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text='{"chart_type":"line"}')])

    class FakeAnthropic:
        def __init__(self, api_key):
            seen["api_key"] = api_key
            self.messages = FakeMessages()

    fake_module = SimpleNamespace(Anthropic=FakeAnthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    result = _extract_with_anthropic(b"img", api_key="sk-ant", model="claude-3-5-sonnet-20241022")

    assert result["chart_type"] == "line"
    assert seen["messages"][0]["content"][0]["source"]["data"]
