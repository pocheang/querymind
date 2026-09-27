"""The four feed parsers, against trimmed real records (`tests/fixtures/threat_intel/`).

The fixtures are real: two NVD CVE API 2.0 records, twelve KEV entries, fourteen
EPSS rows and a cut of the ATT&CK v19.2 enterprise bundle, trimmed only in size.
CI never downloads anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.threat_intel.parsers import (
    parse_attack_bundle,
    parse_epss_csv,
    parse_kev,
    parse_nvd_page,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "threat_intel"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --- NVD -----------------------------------------------------------------------------------


def test_nvd_records_carry_nvds_own_primary_score_and_its_source():
    rows = {row.cve_id: row for row in parse_nvd_page(_json("nvd_page.json")).rows}

    log4shell = rows["CVE-2021-44228"]
    assert (log4shell.cvss_score, log4shell.severity, log4shell.cvss_version) == (10.0, "CRITICAL", "3.1")
    assert log4shell.cvss_source == "nvd@nist.gov"
    assert rows["CVE-2022-22965"].cvss_score == 9.8
    assert rows["CVE-2022-22965"].cwe == ("CWE-94",)


def test_only_vulnerable_cpe_matches_are_kept_with_their_bounds():
    """Spring4Shell's configuration also names JDK >= 9 as `vulnerable: false` -- a precondition, not a product."""

    spring = next(row for row in parse_nvd_page(_json("nvd_page.json")).rows if row.cve_id == "CVE-2022-22965")
    products = {(r.vendor, r.product) for r in spring.ranges}

    assert ("oracle", "jdk") not in products
    framework = [r for r in spring.ranges if r.product == "spring_framework"]
    assert {(r.start_including, r.end_excluding) for r in framework} >= {("", "5.2.20"), ("5.3.0", "5.3.18")}


def test_nvd_prose_is_not_carried():
    """Descriptions are third-party text: nothing downstream may put them in a model's context."""

    for row in parse_nvd_page(_json("nvd_page.json")).rows:
        assert not hasattr(row, "description")


def test_a_malformed_nvd_record_is_dropped_and_counted():
    page = _json("nvd_page.json")
    page["vulnerabilities"].append({"cve": {"id": "CVE-XXXX-1", "published": "2024-01-01T00:00:00"}})
    page["vulnerabilities"].append({"cve": {"id": "CVE-2024-12345", "published": "yesterday"}})

    result = parse_nvd_page(page)

    assert result.rejected == 2
    assert len(result.rows) == 2


def test_an_out_of_range_score_is_not_a_score():
    page = _json("nvd_page.json")
    metric = page["vulnerabilities"][0]["cve"]["metrics"]["cvssMetricV31"][0]
    metric["cvssData"]["baseScore"] = 42

    row = parse_nvd_page(page).rows[0]

    assert row.cvss_score is None
    assert row.severity == "" and row.cvss_source == ""


# --- KEV -----------------------------------------------------------------------------------


def test_kev_entries_parse_with_their_dates():
    rows = {row.cve_id: row for row in parse_kev(_json("kev.json")).rows}

    spring = rows["CVE-2022-22965"]
    assert (spring.date_added, spring.due_date) == ("2022-04-04", "2022-04-25")
    assert len(rows) == 12


def test_a_kev_entry_without_a_valid_id_or_date_is_dropped():
    payload = {
        "vulnerabilities": [
            {"cveID": "not-a-cve", "dateAdded": "2024-01-01"},
            {"cveID": "CVE-2024-1234", "dateAdded": "soon"},
        ]
    }

    result = parse_kev(payload)

    assert result.rows == () and result.rejected == 2


# --- EPSS ----------------------------------------------------------------------------------


def test_epss_rows_and_the_feeds_own_score_date():
    as_of, result = parse_epss_csv((FIXTURES / "epss.csv").read_text(encoding="utf-8"))

    assert as_of == "2026-09-26"
    scores = {row.cve_id: row for row in result.rows}
    assert scores["CVE-2021-44228"].score == pytest.approx(0.99999)


def test_an_epss_feed_without_a_score_date_is_refused():
    """A probability without a date is not something a reader can weigh."""

    with pytest.raises(ValueError, match="score_date"):
        parse_epss_csv("cve,epss,percentile\nCVE-2024-1234,0.1,0.5\n")


def test_an_epss_probability_outside_zero_to_one_is_dropped():
    text = "#model_version:v1,score_date:2026-09-26T00:00:00Z\ncve,epss,percentile\nCVE-2024-1234,1.5,0.5\nCVE-2024-1235,0.1,0.5\n"

    _, result = parse_epss_csv(text)

    assert [row.cve_id for row in result.rows] == ["CVE-2024-1235"] and result.rejected == 1


# --- ATT&CK -------------------------------------------------------------------------------


def test_attack_detection_comes_from_detection_strategies():
    """Since ATT&CK v18 `x_mitre_detection` is empty; reading only it would report no detection for anything."""

    bundle = parse_attack_bundle(_json("enterprise-attack.json"))

    detections = [d for d in bundle.detections if d.technique_id == "T1190"]
    assert detections and detections[0].strategy_id == "DET0080"


def test_attack_mitigations_version_and_subtechniques():
    bundle = parse_attack_bundle(_json("enterprise-attack.json"))
    techniques = {t.technique_id: t for t in bundle.techniques}

    assert bundle.version == "19.2"
    assert {m.mitigation_id for m in bundle.mitigations if m.technique_id == "T1190"} >= {"M1048", "M1050", "M1051"}
    assert techniques["T1059.001"].parent_id == "T1059" and techniques["T1059.001"].is_subtechnique
    assert techniques["T1190"].tactics == ("initial-access",)


def test_a_revoked_technique_is_kept_and_marked():
    """Kept so a lookup can say 'revoked' rather than 'unknown'; never offered as current."""

    techniques = {t.technique_id: t for t in parse_attack_bundle(_json("enterprise-attack.json")).techniques}

    assert techniques["T1066"].revoked


def test_the_summary_is_one_sentence_without_citation_markers():
    bundle = {
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--1",
                "name": "Example",
                "description": "Adversaries do X (Citation: Somebody 2020). Second sentence here.",
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "T9999",
                        "url": "https://attack.mitre.org/techniques/T9999",
                    }
                ],
            }
        ]
    }

    (technique,) = parse_attack_bundle(bundle).techniques

    assert technique.summary == "Adversaries do X ."
