"""The 2026-09-23 tool-layer review: each defect below was reproduced before it was fixed.

Most of them share a shape: a tool that answered `succeeded` with something the
model then cited -- a number off by 4x, a CVSS score in the wrong severity band,
one technique out of three -- or a failure that took more down with it than
itself.
"""

from __future__ import annotations

import http.server
import logging
import pathlib
import tempfile
import threading
import traceback
from pathlib import Path
from urllib.parse import quote

import pytest

from app.core.config import get_settings
from app.mcp.approvals import ApprovalStore
from app.mcp.audit import AuditLog
from app.mcp.authorization import AuthorizationPolicy
from app.mcp.contracts import ToolArgument, ToolCall
from app.mcp.registry import ToolRegistry
from app.orchestration.request import RequestActor
from app.tools.ai.code_sandbox import evaluate_safe_math
from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory
from app.tools.cyber.cve_tools import (
    _CURATED_CVE_DB,
    ATTACK_TOOL_DEFINITION,
    CVE_TOOL_DEFINITION,
    execute_cve_lookup,
    execute_mitre_attack_lookup,
)
from app.tools.registry import DomainToolRegistry
from app.tools.web.base import WebSearchError, describe_search_error
from app.tools.web.providers.searxng import SearXNGSearchProvider


def _scratch_db() -> Path:
    """Approvals live in SQLite; a test's belong in a throwaway file, never the developer's app.db."""
    return Path(tempfile.mkdtemp()) / "app.db"


ACTOR = RequestActor(user_id="u", tenant_id="t", role="user")


def _call(tool_id: str, **arguments: str) -> ToolCall:
    return ToolCall(tool_id=tool_id, arguments=tuple(ToolArgument(name=k, value=v) for k, v in arguments.items()))


async def _cve(value: str):
    return await execute_cve_lookup(_call(CVE_TOOL_DEFINITION.tool_id, cve_id=value), ACTOR)


async def _attack(value: str):
    return await execute_mitre_attack_lookup(_call(ATTACK_TOOL_DEFINITION.tool_id, technique_id=value), ACTOR)


# --- the math tool: keyword arguments ------------------------------------------


def test_a_keyword_argument_is_not_dropped():
    # Measured before the fix: 512 against 2048 -- batch_size was ignored.
    positional = evaluate_safe_math("kv_cache_mb(32, 8, 128, 4096, 4)")
    keyword = evaluate_safe_math("kv_cache_mb(32, 8, 128, 4096, batch_size=4)")

    assert keyword == positional == 2048.0


def test_a_builtin_keyword_argument_is_honoured():
    assert evaluate_safe_math("round(3.14159, ndigits=2)") == 3.14  # was 3


def test_keyword_unpacking_is_refused_rather_than_guessed():
    with pytest.raises((ValueError, SyntaxError)):
        evaluate_safe_math("round(3.14159, **{'ndigits': 2})")


def test_an_unknown_keyword_fails_instead_of_being_ignored():
    with pytest.raises(TypeError):
        evaluate_safe_math("kv_cache_mb(32, 8, 128, 4096, batch=4)")


def test_a_boolean_is_not_a_number():
    with pytest.raises(ValueError, match="bool"):
        evaluate_safe_math("True + True")  # was 2


# --- the curated CVE table agrees with NVD, and says so ------------------------


@pytest.mark.parametrize(
    ("key", "score", "severity"),
    [
        # Each was checked against the NVD API on 2026-09-23.
        ("cve-2023-38606", 5.5, "MEDIUM"),  # was 8.8 HIGH
        ("cve-2017-0144", 8.8, "HIGH"),  # EternalBlue, was 9.8 CRITICAL
        ("cve-2017-5638", 9.8, "CRITICAL"),  # Struts2 S2-045, was 10.0
        ("cve-2023-4966", 7.5, "HIGH"),  # CitrixBleed, was Citrix's own 9.4
    ],
)
def test_the_corrected_scores_are_nvds(key: str, score: float, severity: str):
    entry = _CURATED_CVE_DB[key]
    assert (entry["cvss"], entry["severity"]) == (score, severity)


def test_every_score_names_its_source_and_date():
    for key, entry in _CURATED_CVE_DB.items():
        assert entry.get("cvss_source"), key
        assert entry.get("cvss_as_of"), key


def test_every_affected_range_and_mitigation_names_its_source():
    for key, entry in _CURATED_CVE_DB.items():
        assert entry.get("affected_source"), key
        assert entry.get("mitigation_source"), key


@pytest.mark.parametrize(
    ("key", "must_contain"),
    [
        # Each read narrower than NVD, telling someone on an affected version
        # they were safe.
        ("cve-2022-22965", "before 5.2.20"),  # was "5.2.0 to 5.2.19": older lines affected too
        ("cve-2017-5638", "2.2.3 to before 2.3.32"),  # was "2.3.5 - 2.3.31"
        ("cve-2023-4966", "12.1 to before 12.1-55.300"),  # 12.1 was missing
        # The old text already said "macOS" as a bare word, so a version is what
        # tells the two apart.
        ("cve-2023-38606", "12.0.0 to before 12.6.8"),  # was "iOS before 16.6, iPadOS, macOS"
    ],
)
def test_affected_ranges_are_not_narrower_than_nvd(key: str, must_contain: str):
    assert must_contain in _CURATED_CVE_DB[key]["affected"]


def test_log4shell_offers_no_workaround_apache_does_not():
    mitigation = _CURATED_CVE_DB["cve-2021-44228"]["mitigation"]

    assert "formatMsgNoLookups" not in mitigation
    assert "2.15.0" in mitigation
    assert "2.12.2" in mitigation
    assert "2.3.1" in mitigation


def test_the_xz_mitigation_names_a_real_release():
    mitigation = _CURATED_CVE_DB["cve-2024-3094"]["mitigation"]

    assert "repack" not in mitigation  # a build tukaani.org never mentions
    assert "5.6.2" in mitigation


@pytest.mark.asyncio
async def test_the_answer_states_where_the_score_came_from():
    result = await _cve("CVE-2023-38606")

    assert result.status == "succeeded"
    assert "5.5 MEDIUM" in result.summary
    assert "NVD" in result.summary
    assert _CURATED_CVE_DB["cve-2023-38606"]["cvss_as_of"] in result.summary


# --- product names are not vulnerabilities -------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("product", ["log4j", "runc", "xz", "webp", "struts2", "ms17-010"])
async def test_a_product_name_does_not_resolve_to_one_cve(product: str):
    result = await _cve(product)

    # "log4j" was answered with Log4Shell as a success, as though it were the
    # product's only CVE.
    assert result.status == "failed"
    assert "not a complete list" in result.summary


@pytest.mark.asyncio
@pytest.mark.parametrize("nickname", ["log4shell", "heartbleed", "xz backdoor", "永恒之蓝"])
async def test_a_vulnerability_nickname_still_resolves(nickname: str):
    assert (await _cve(nickname)).status == "succeeded"


@pytest.mark.asyncio
async def test_a_longer_digit_run_is_not_truncated_into_another_id():
    result = await _cve("CVE-2021-442281234")

    # Was looked up as CVE-2021-4422812, a different identifier. It is now
    # rejected as malformed; the summary echoes the input, so the assertion is
    # on the verdict rather than on digits the echo contains anyway.
    assert result.status == "failed"
    assert result.summary.startswith("Invalid CVE format")


# --- MITRE: exact resolution only ----------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("fragment", ["", "a", "on", "defense", "access"])
async def test_a_fragment_resolves_to_nothing(fragment: str):
    # Each was a `succeeded` T1190 or T1078: the fuzzy step matched the INPUT as
    # a substring of a technique's name or tactic and took the first hit.
    assert (await _attack(fragment)).status == "failed"


@pytest.mark.asyncio
async def test_a_tactic_lists_every_curated_technique_under_it():
    result = await _attack("Initial Access")

    assert result.status == "succeeded"
    for technique in ("T1190", "T1566", "T1078"):
        assert technique in result.summary
    assert "not the full matrix" in result.summary


@pytest.mark.asyncio
async def test_a_sub_technique_falls_back_to_its_parent_and_says_so():
    result = await _attack("T1059.001")

    assert result.status == "succeeded"
    assert "[T1059]" in result.summary
    assert "parent technique" in result.summary


@pytest.mark.asyncio
@pytest.mark.parametrize(("value", "technique"), [("Phishing", "T1566"), ("t1190", "T1190"), ("钓鱼", "T1566")])
async def test_exact_names_ids_and_aliases_still_resolve(value: str, technique: str):
    result = await _attack(value)

    assert result.status == "succeeded"
    assert f"[{technique}]" in result.summary


# --- a failed web search does not log the question ------------------------------

QUESTION = "我们公司的并购目标是哪家"


class _Throttled(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib naming
        self.send_response(429)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def throttled_searxng():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Throttled)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def _carries_question(text: str) -> bool:
    return QUESTION in text or quote(QUESTION) in text


def test_a_failed_search_logs_and_raises_without_the_question(throttled_searxng, caplog):
    """Driven through the real provider against a server that answers 429.

    The provider logged `question_ref(query)` and then `str(exc)`, and an httpx
    error's message is the request URL -- the question, URL-encoded. It then
    re-raised that exception, and the caller's `logger.exception` printed it a
    third time. Measured before the fix: two log lines, both carrying it.
    """

    settings = get_settings().model_copy(update={"searxng_base_url": throttled_searxng, "web_search_max_retries": 0})

    # Built outside the `raises` block: a constructor that raised would
    # otherwise pass this test for the wrong reason.
    provider = SearXNGSearchProvider(settings)
    with caplog.at_level(logging.DEBUG), pytest.raises(WebSearchError) as raised:
        provider.search(QUESTION)

    assert caplog.records, "the failure must still be logged"
    assert not [r for r in caplog.records if _carries_question(r.getMessage())]
    # What the caller's `logger.exception` would print -- chained context included.
    assert not _carries_question("".join(traceback.format_exception(raised.value)))
    assert "429" in str(raised.value)


def test_no_provider_puts_an_exception_message_in_a_log_line():
    # A recurrence guard over all four providers, not just the one driven above.
    for path in sorted(pathlib.Path("app/tools/web/providers").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "str(exc)" not in source, path
        assert "str(last_err)" not in source, path
        assert "raise last_err" not in source, path


@pytest.mark.parametrize("logger_name", ["httpx", "ddgs.ddgs", "primp"])
def test_http_client_libraries_do_not_log_the_query(logger_name: str, caplog):
    """The libraries' own lines, on their real logger names, including a child logger.

    ddgs logs each failing engine as `Error in engine %s: %r` with primp's error,
    whose text is `error sending request for url (<url>)`. Measured against a
    refusing proxy before the fix: seven lines carrying the question for one
    search. `ddgs.ddgs` is a child logger, which is why a filter on `ddgs` would
    not have seen these records.
    """

    import app.tools.web.base  # noqa: F401  - installs the redaction, as the app does

    url = f"https://www.example-search.com/search?q={quote(QUESTION)}&format=json"
    error = ConnectionError(f"error sending request for url ({url})")

    with caplog.at_level(logging.DEBUG):
        logging.getLogger(logger_name).info("Error in engine %s: %r", "example", error)

    message = caplog.records[-1].getMessage()
    assert not _carries_question(message)
    assert "https://www.example-search.com/search?<query redacted>" in message


def test_the_application_s_own_log_lines_are_left_alone(caplog):
    # Scope: only the HTTP client libraries are rewritten. The application's own
    # lines are covered by `question_ref` and the AST guard over its logger calls.
    import app.tools.web.base  # noqa: F401

    with caplog.at_level(logging.DEBUG):
        logging.getLogger("app.example").info("fetched %s", "https://example.com/page?id=7")

    assert caplog.records[-1].getMessage() == "fetched https://example.com/page?id=7"


def test_the_error_description_carries_type_and_status_only():
    class _Response:
        status_code = 503

    class _Failure(Exception):
        response = _Response()

    assert describe_search_error(_Failure("https://search.example/?q=secret")) == "_Failure (HTTP 503)"
    assert describe_search_error(ValueError("q=secret")) == "ValueError"


# --- an extension may override a built-in tool id -------------------------------


class _LiveCveProvider(BaseToolProvider):
    """What replacing the curated table with a live feed looks like."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CYBERSECURITY

    @property
    def tool_definitions(self):
        return (CVE_TOOL_DEFINITION,)

    def get_executor(self, tool_id: str):
        async def live(call, actor):
            del call, actor
            raise AssertionError("never executed here")

        return live


def _mcp_registry() -> ToolRegistry:
    return ToolRegistry(
        authorization=AuthorizationPolicy(),
        approvals=ApprovalStore(_scratch_db()),
        audit=AuditLog(write=lambda _record: None),  # never the developer's audit_logs
    )


def _executor_for(registry: ToolRegistry, tool_id: str):
    return registry._tools[tool_id][1]


@pytest.mark.parametrize("extension_first", [False, True], ids=["after-defaults", "before-defaults"])
def test_a_later_provider_owns_a_tool_id_it_redeclares(extension_first: bool):
    domain = DomainToolRegistry()
    extension = _LiveCveProvider()
    if extension_first:
        domain.register_provider(extension)  # before the built-ins are loaded
    else:
        domain.list_all_tools()
        domain.register_provider(extension)
    mcp = _mcp_registry()

    # Used to raise `ValueError: tool already registered`, which made the whole
    # governed tool stack fail to build on every call.
    domain.register_all_into(mcp)

    assert _executor_for(mcp, CVE_TOOL_DEFINITION.tool_id).__qualname__.endswith("live")
    assert ATTACK_TOOL_DEFINITION.tool_id in mcp._tools, "the other built-in tools still register"


def test_a_provider_registered_after_export_is_reported(caplog):
    domain = DomainToolRegistry()
    domain.register_all_into(_mcp_registry())

    with caplog.at_level(logging.WARNING, logger="app.tools.registry"):
        domain.register_provider(_LiveCveProvider())

    assert any("after the tool stack was built" in r.getMessage() for r in caplog.records)
