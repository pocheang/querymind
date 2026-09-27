"""The security specialist's tools answer from the synced threat-intelligence store.

They used to read a hand-maintained table of a few dozen CVEs and a 9-technique
ATT&CK subset. Now the store (plan PR 6) answers first and the table is the
fallback for an installation that has never synced. Every sentence is built by
code from structured fields -- NVD's description text is never stored, so it
cannot appear -- and every answer says which copy it came from and whether that
copy is stale.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.mcp.contracts import ToolArgument, ToolCall
from app.orchestration.request import RequestActor
from app.services.threat_intel import status as status_module
from app.services.threat_intel.store import ThreatIntelStore
from app.services.threat_intel.sync import sync_source
from app.tools.cyber import intel
from app.tools.cyber.cve_tools import execute_cve_lookup, execute_mitre_attack_lookup, execute_product_exposure

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "threat_intel"
ACTOR = RequestActor(user_id="u", tenant_id="t", role="viewer")


def _import_dir(root: Path) -> Path:
    directory = root / "import"
    (directory / "nvd").mkdir(parents=True)
    shutil.copy(FIXTURES / "kev.json", directory / "known_exploited_vulnerabilities.json")
    (directory / "epss_scores-current.csv.gz").write_bytes(gzip.compress((FIXTURES / "epss.csv").read_bytes()))
    shutil.copy(FIXTURES / "enterprise-attack.json", directory / "enterprise-attack.json")
    shutil.copy(FIXTURES / "nvd_page.json", directory / "nvd" / "page-0001.json")
    return directory


@pytest.fixture
def store(tmp_path, monkeypatch) -> ThreatIntelStore:
    synced = ThreatIntelStore(tmp_path / "ti.db")
    directory = _import_dir(tmp_path)
    for source in ("nvd", "kev", "epss", "attack"):
        assert sync_source(source, synced, from_dir=directory).status == "succeeded"
    monkeypatch.setattr(intel, "get_threat_intel_store", lambda: synced)
    return synced


@pytest.fixture
def empty_store(tmp_path, monkeypatch) -> ThreatIntelStore:
    empty = ThreatIntelStore(tmp_path / "empty.db")
    monkeypatch.setattr(intel, "get_threat_intel_store", lambda: empty)
    return empty


def _run(executor, tool_id: str, **arguments: str):
    call = ToolCall(tool_id=tool_id, arguments=tuple(ToolArgument(name=k, value=v) for k, v in arguments.items()))
    return asyncio.run(executor(call, ACTOR))


def _cve(**arguments):
    return _run(execute_cve_lookup, "querymind_cyber_cve_lookup", **arguments)


def _attack(**arguments):
    return _run(execute_mitre_attack_lookup, "querymind_cyber_mitre_attack", **arguments)


def _exposure(**arguments):
    return _run(execute_product_exposure, "querymind_cyber_product_exposure", **arguments)


# --- CVE --------------------------------------------------------------------------------------


def test_a_cve_answer_carries_nvd_kev_and_epss_with_their_sources_and_dates(store):
    result = _cve(cve_id="CVE-2022-22965")

    assert result.status == "succeeded"
    summary = result.summary
    assert "CVSS 3.1 9.8 CRITICAL (source nvd@nist.gov)" in summary
    assert "CWE-94" in summary
    assert "CISA KEV: listed since 2022-04-04" in summary
    assert "EPSS:" in summary and "scored 2026-09-26" in summary
    assert "local NVD copy synced" in summary and "local KEV copy synced" in summary
    assert "spring_framework >= 5.3.0, < 5.3.18" in summary


def test_nvd_description_text_never_reaches_a_summary(store):
    """Third-party prose is not stored, so a tool result cannot carry it into the model's context."""

    page = json.loads((FIXTURES / "nvd_page.json").read_text(encoding="utf-8"))
    descriptions = [d["value"] for v in page["vulnerabilities"] for d in v["cve"]["descriptions"]]

    for cve_id in ("CVE-2021-44228", "CVE-2022-22965"):
        summary = _cve(cve_id=cve_id).summary
        assert not any(text[:60] in summary for text in descriptions)


def test_the_curated_vendor_mitigation_is_kept_beside_the_store(store):
    """Nothing synced carries remediation text; the curated table's advisory does."""

    summary = _cve(cve_id="Log4Shell").summary

    assert summary.startswith("Log4Shell: [CVE-2021-44228]")
    assert "logging.apache.org/log4j/2.x/security.html" in summary


def test_a_cve_the_synced_store_lacks_is_a_miss_that_claims_nothing(store):
    result = _cve(cve_id="CVE-2019-99999")

    assert result.status == "failed"
    assert "local NVD copy" in result.summary
    assert "says nothing about whether the CVE exists" in result.summary


def test_a_never_synced_store_falls_back_to_the_curated_table_and_says_so(empty_store):
    hit = _cve(cve_id="CVE-2021-44228")
    miss = _cve(cve_id="CVE-2019-99999")

    assert hit.status == "succeeded" and "CVSS 10.0" in hit.summary
    assert miss.status == "failed" and "has not been synced" in miss.summary


def test_a_stale_source_says_so_in_the_answer(store, monkeypatch):
    later = datetime.now(UTC) + timedelta(days=30)
    real = status_module.source_statuses
    monkeypatch.setattr(intel, "source_statuses", lambda s, settings=None: real(s, settings, now=later))

    summary = _cve(cve_id="CVE-2022-22965").summary

    assert "STALE: older than" in summary


# --- ATT&CK -----------------------------------------------------------------------------------


def test_a_technique_comes_from_the_full_matrix(store):
    result = _attack(technique_id="T1190")

    assert result.status == "succeeded"
    assert "version 19.2" in result.summary
    assert "DET0080" in result.summary
    assert "M1048 Application Isolation and Sandboxing" in result.summary
    assert ".." not in result.summary


def test_a_chinese_alias_and_an_english_name_resolve(store):
    assert "[T1059] Command and Scripting Interpreter" in _attack(technique_id="powershell").summary
    assert _attack(technique_id="Exploit Public-Facing Application").summary.startswith("[T1190]")


def test_a_tactic_lists_its_techniques(store):
    result = _attack(technique_id="execution")

    assert result.status == "succeeded" and "[T1059]" in result.summary


def test_a_revoked_technique_says_so(store):
    result = _attack(technique_id="T1066")

    assert result.status == "failed" and "revoked" in result.summary


def test_an_unknown_technique_is_a_miss(store):
    result = _attack(technique_id="T9999")

    assert result.status == "failed" and "local copy of MITRE ATT&CK" in result.summary


# --- product exposure ------------------------------------------------------------------------


def test_a_version_inside_a_range_is_affected(store):
    result = _exposure(product="spring_framework", version="5.3.17", vendor="vmware")

    assert result.status == "succeeded"
    assert "CVE-2022-22965" in result.summary and "in KEV since 2022-04-04" in result.summary


def test_the_excluded_end_of_a_range_is_not_affected(store):
    result = _exposure(product="spring_framework", version="5.3.18", vendor="vmware")

    assert "CVE-2022-22965" not in result.summary


def test_a_release_candidate_sorts_before_its_release(store):
    """2.15.0-rc1 < 2.15.0: a range ending before 2.15.0 includes the release candidate (plan 2.5)."""

    affected = _exposure(product="log4j", version="2.15.0-rc1", vendor="apache").summary
    fixed = _exposure(product="log4j", version="2.17.1", vendor="apache").summary

    assert "CVE-2021-44228" in affected
    assert "CVE-2021-44228" not in fixed


def test_a_version_that_cannot_be_compared_is_approximate_not_guessed(store):
    summary = _exposure(product="spring_framework", version="5.3.x-custom-build", vendor="vmware").summary

    assert "approximate" in summary and "cannot be compared" in summary


def test_the_product_name_is_matched_the_way_nvd_writes_it(store):
    assert "CVE-2022-22965" in _exposure(product="Spring Framework", version="5.3.17").summary


def test_an_unknown_product_is_not_declared_safe(store):
    result = _exposure(product="no_such_product", version="1.0")

    assert result.status == "failed" and "not evidence that the product is safe" in result.summary


def test_without_a_version_it_lists_and_asks_for_one(store):
    summary = _exposure(product="spring_framework", vendor="vmware").summary

    assert "name spring_framework" in summary and "Give a version" in summary


def test_kev_listed_cves_come_first(store):
    rows = [
        {"kev_added": None, "epss_score": 0.9, "cvss_score": 10.0},
        {"kev_added": "2024-01-01", "epss_score": 0.1, "cvss_score": 5.0},
    ]

    assert sorted(rows, key=intel._priority, reverse=True)[0]["kev_added"] == "2024-01-01"


def test_a_never_synced_store_falls_back_to_the_curated_table_without_a_verdict(empty_store):
    """Plan acceptance A3: say where the data came from, and never turn 'not compared' into 'safe'."""

    result = _exposure(product="log4j", version="2.14.1")

    assert result.status == "succeeded"
    assert "has not been synced" in result.summary
    assert "NOT a complete list" in result.summary and "does not compare versions" in result.summary
    assert "CVE-2021-44228" in result.summary


def test_a_never_synced_store_and_an_uncurated_product_is_a_plain_miss(empty_store):
    result = _exposure(product="no_such_product", version="1.0")

    assert result.status == "failed" and "has not been synced" in result.summary


def test_the_tool_is_read_only_and_in_the_security_category():
    from app.tools.cyber.cve_tools import PRODUCT_EXPOSURE_TOOL_DEFINITION as definition

    assert (definition.operation, definition.risk, definition.category) == ("read", "read_only", "cybersecurity")
    assert "not evidence the product is safe" in definition.description.lower()
