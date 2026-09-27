"""Tool summaries built from the local threat-intelligence store.

Every sentence here is assembled by code from structured fields, which is what
lets a tool result be cited as `[T{k}]`: nothing in it was written by a third
party except MITRE's one-sentence technique summary, which is attributed. NVD's
description text is not stored, so it cannot appear.

Each summary names its source and when the local copy was last synced, and
says so plainly when that copy is stale -- a reader acting on "not in KEV" needs
to know whether "KEV" means this morning or last quarter.
"""

from __future__ import annotations

from dataclasses import dataclass

from packaging.version import InvalidVersion, Version

from app.services.threat_intel.status import SourceStatus, get_threat_intel_store, source_statuses
from app.services.threat_intel.store import ThreatIntelStore

__all__ = [
    "IntelAnswer",
    "cve_intel",
    "product_exposure",
    "store_is_empty",
    "tactic_intel",
    "technique_intel",
    "technique_id_by_name",
]

MAX_RANGES_SHOWN = 5
MAX_EXPOSURES_SHOWN = 10


@dataclass(frozen=True)
class IntelAnswer:
    status: str  # succeeded | failed
    summary: str
    empty_store: bool = False  # the source was never synced; the caller may fall back


def _store() -> ThreatIntelStore:
    return get_threat_intel_store()


def _statuses() -> dict[str, SourceStatus]:
    return {status.source: status for status in source_statuses(_store())}


def store_is_empty(source: str) -> bool:
    return _statuses()[source].state == "empty"


def _as_of(status: SourceStatus, label: str) -> str:
    """'local NVD copy synced 2026-09-27' -- plus a warning when it is past its threshold."""

    day = status.last_success[:10] or "never"
    text = f"local {label} copy synced {day}"
    if status.data_version:
        text += f", version {status.data_version}"
    if status.state == "stale":
        text += f"; STALE: older than {status.stale_after_days} days"
    return text


# --- CVE -------------------------------------------------------------------------------------


def cve_intel(cve_id: str) -> str | None:
    """What the local store says about one CVE, or None when it holds nothing on it."""

    record = _store().cve(cve_id)
    if record is None:
        return None
    statuses = _statuses()
    parts = [
        _cve_score_line(record, statuses["nvd"]),
        _kev_line(record, statuses["kev"]),
        _epss_line(record, statuses["epss"]),
    ]
    ranges = _ranges_line(_primary_first(record["ranges"], record["kev"]))
    if ranges:
        parts.append(ranges)
    return " ".join(part for part in parts if part)


def _cve_score_line(record: dict, nvd: SourceStatus) -> str:
    cve = record["cve"]
    if cve is None:
        return f"[{record['kev']['cve_id']}] not in the {_as_of(nvd, 'NVD')}."
    if cve["cvss_score"] is None:
        score = "no CVSS score assigned yet"
    else:
        score = f"CVSS {cve['cvss_version']} {cve['cvss_score']:.1f} {cve['severity']} (source {cve['cvss_source'] or 'unstated'})"
    cwe = f" Weakness: {cve['cwe'].replace(',', ', ')}." if cve["cwe"] else ""
    return (
        f"[{cve['cve_id']}] {score}; NVD status {cve['status'] or 'unknown'}, published {cve['published'][:10]} "
        f"({_as_of(nvd, 'NVD')}).{cwe}"
    )


def _kev_line(record: dict, kev_status: SourceStatus) -> str:
    kev = record["kev"]
    if kev_status.state == "empty":
        return "CISA KEV: not synced here, so exploitation status is unknown."
    if kev is None:
        return f"CISA KEV: not listed ({_as_of(kev_status, 'KEV')})."
    due = f", remediation due {kev['due_date']}" if kev["due_date"] else ""
    return (
        f"CISA KEV: listed since {kev['date_added']}{due}; known ransomware use: {kev['known_ransomware'] or 'unknown'}; "
        f"required action: {kev['required_action']} ({_as_of(kev_status, 'KEV')})."
    )


def _epss_line(record: dict, epss_status: SourceStatus) -> str:
    epss = record["epss"]
    if epss is None:
        return "" if epss_status.state == "empty" else "EPSS: no score."
    return (
        f"EPSS: {epss['score']:.4f} probability of exploitation in 30 days, percentile {epss['percentile']:.3f} "
        f"(FIRST, scored {epss['as_of']})."
    )


def _primary_first(ranges: list[dict], kev: dict | None) -> list[dict]:
    """The CVE's own product first: the one KEV names, then the most-listed product.

    NVD lists every product that bundles a component, alphabetically, so for
    Spring4Shell the first five ranges were other vendors' products and Spring
    Framework itself fell outside what the summary shows.
    """

    kev_product = "_".join(str((kev or {}).get("product") or "").lower().split())
    counts: dict[tuple[str, str], int] = {}
    for row in ranges:
        counts[(row["vendor"], row["product"])] = counts.get((row["vendor"], row["product"]), 0) + 1
    return sorted(
        ranges,
        key=lambda row: (
            row["product"] != kev_product,
            -counts[(row["vendor"], row["product"])],
            row["vendor"],
            row["product"],
        ),
    )


def _ranges_line(ranges: list[dict]) -> str:
    if not ranges:
        return ""
    shown = "; ".join(_range_text(r) for r in ranges[:MAX_RANGES_SHOWN])
    more = f" (first {MAX_RANGES_SHOWN} of {len(ranges)})" if len(ranges) > MAX_RANGES_SHOWN else ""
    return f"Affected, per NVD CPE configurations{more}: {shown}."


def _range_text(row: dict) -> str:
    bounds = [
        f">= {row['start_including']}" if row["start_including"] else "",
        f"> {row['start_excluding']}" if row["start_excluding"] else "",
        f"<= {row['end_including']}" if row["end_including"] else "",
        f"< {row['end_excluding']}" if row["end_excluding"] else "",
    ]
    version = row["version"] if row["version"] not in ("*", "-", "") else ""
    span = version or ", ".join(bound for bound in bounds if bound) or "all versions"
    return f"{row['vendor']} {row['product']} {span}"


# --- product exposure ------------------------------------------------------------------------


def product_exposure(product: str, version: str = "", vendor: str = "") -> IntelAnswer:
    """Which CVEs in the local NVD copy name this product, and which reach this version.

    Ordered by what a responder acts on first: listed in KEV, then EPSS, then
    CVSS. A version that cannot be compared with a range (vendor-specific
    formats) is reported as approximate rather than guessed.
    """

    statuses = _statuses()
    if statuses["nvd"].state == "empty":
        return IntelAnswer(
            "failed",
            "The local NVD copy has not been synced, so no product can be checked here; "
            "this says nothing about whether the product is affected.",
            empty_store=True,
        )
    rows, cpe_product = _product_rows(product, vendor)
    if not rows:
        return IntelAnswer(
            "failed",
            f"No CVE in the {_as_of(statuses['nvd'], 'NVD')} names the product '{product}'. NVD names products "
            "by CPE (for example 'log4j', 'spring_framework', 'http_server'); absence here is not evidence "
            "that the product is safe.",
        )
    exposures, approximate = _matching(rows, version)
    return IntelAnswer("succeeded", _exposure_summary(cpe_product, version, exposures, approximate, statuses))


def _product_rows(product: str, vendor: str) -> tuple[list[dict], str]:
    base = product.strip().lower()
    for candidate in dict.fromkeys((base, base.replace(" ", "_"), base.replace(" ", "-"), base.replace("-", "_"))):
        rows = _store().product_ranges(candidate, vendor or None)
        if rows:
            return rows, candidate
    return [], base


def _matching(rows: list[dict], version: str) -> tuple[dict[str, dict], set[str]]:
    exposures: dict[str, dict] = {}
    approximate: set[str] = set()
    for row in rows:
        verdict = _version_in_range(version, row) if version else True
        if verdict is False:
            continue
        if verdict is None:
            approximate.add(row["cve_id"])
        exposures.setdefault(row["cve_id"], {**row, "range_text": _range_text(row)})
    return exposures, approximate


def _version_in_range(version: str, row: dict) -> bool | None:
    """True / False, or None when the versions cannot be compared."""

    exact = row["version"]
    try:
        wanted = Version(version)
        if exact not in ("*", "-", ""):
            return Version(exact) == wanted
        checks = (
            (row["start_including"], lambda bound: wanted >= bound),
            (row["start_excluding"], lambda bound: wanted > bound),
            (row["end_including"], lambda bound: wanted <= bound),
            (row["end_excluding"], lambda bound: wanted < bound),
        )
        return all(check(Version(bound)) for bound, check in checks if bound)
    except InvalidVersion:
        return None


def _priority(row: dict) -> tuple:
    return (row["kev_added"] is not None, row["epss_score"] or 0.0, row["cvss_score"] or 0.0)


def _exposure_summary(
    product: str, version: str, exposures: dict[str, dict], approximate: set[str], statuses: dict[str, SourceStatus]
) -> str:
    ordered = sorted(exposures.values(), key=_priority, reverse=True)
    listed = "; ".join(_exposure_line(row, row["cve_id"] in approximate) for row in ordered[:MAX_EXPOSURES_SHOWN])
    subject = f"{product} {version}" if version else product
    scope = "affect" if version else "name"
    count = f"{len(ordered)} CVE{'s' if len(ordered) != 1 else ''}"
    more = (
        f", showing the top {MAX_EXPOSURES_SHOWN} by KEV, then EPSS, then CVSS"
        if len(ordered) > MAX_EXPOSURES_SHOWN
        else ""
    )
    head = f"{count} in the {_as_of(statuses['nvd'], 'NVD')} {scope} {subject}{more}: {listed}."
    if not ordered:
        head = f"No CVE in the {_as_of(statuses['nvd'], 'NVD')} affects {subject} by its version ranges."
    notes = []
    if approximate:
        notes.append(f"{len(approximate)} marked 'approximate' use version formats that cannot be compared exactly.")
    if not version:
        notes.append("Give a version to check exposure rather than list every CVE naming the product.")
    notes.append(f"KEV: {_as_of(statuses['kev'], 'KEV')}. EPSS: {_as_of(statuses['epss'], 'EPSS')}.")
    return " ".join([head, *notes])


def _exposure_line(row: dict, approximate: bool) -> str:
    facts = []
    if row["cvss_score"] is not None:
        facts.append(f"CVSS {row['cvss_score']:.1f} {row['severity']}")
    if row["kev_added"]:
        facts.append(f"in KEV since {row['kev_added']}")
    if row["epss_score"] is not None:
        facts.append(f"EPSS {row['epss_score']:.3f}")
    marker = ", approximate" if approximate else ""
    return f"{row['cve_id']} ({', '.join(facts) or 'no score'}{marker}; range {row['range_text']})"


# --- ATT&CK ------------------------------------------------------------------------------------


def technique_id_by_name(name: str) -> str | None:
    return _store().technique_by_name(name)


def technique_intel(technique_id: str) -> IntelAnswer | None:
    """One technique from the full matrix, or None when the store does not hold it."""

    technique = _store().technique(technique_id)
    if technique is None:
        return None
    attack = _statuses()["attack"]
    if technique["revoked"] or technique["deprecated"]:
        state = "revoked" if technique["revoked"] else "deprecated"
        return IntelAnswer(
            "failed",
            f"{technique['technique_id']} ({technique['name']}) is {state} in MITRE ATT&CK ({_as_of(attack, 'ATT&CK')}); "
            "look up its replacement.",
        )
    return IntelAnswer("succeeded", _technique_summary(technique, attack))


def _technique_summary(technique: dict, attack: SourceStatus) -> str:
    tactics = technique["tactics"].replace(",", ", ") or "none listed"
    parent = f" Sub-technique of {technique['parent_id']}." if technique["parent_id"] else ""
    detections = (
        "; ".join(f"{d['strategy_id']} {d['name']}".strip().rstrip(".") for d in technique["detections"])
        or "none published"
    )
    mitigations = (
        "; ".join(f"{m['mitigation_id']} {m['name']}".rstrip(".") for m in technique["mitigations"]) or "none published"
    )
    subs = technique["subtechniques"]
    sub_text = f" Sub-techniques: {', '.join(s['technique_id'] + ' ' + s['name'] for s in subs[:12])}." if subs else ""
    return (
        f"[{technique['technique_id']}] {technique['name']} (MITRE ATT&CK, {_as_of(attack, 'ATT&CK')}; "
        f"{technique['url'] or 'attack.mitre.org'}).{parent} Tactics: {tactics}. "
        f"MITRE's summary: {technique['summary'] or 'none'} Detection strategies: {detections}. "
        f"Mitigations: {mitigations}.{sub_text}"
    )


def tactic_intel(tactic: str) -> IntelAnswer | None:
    members = _store().techniques_in_tactic(tactic)
    if not members:
        return None
    attack = _statuses()["attack"]
    listed = "; ".join(f"[{m['technique_id']}] {m['name']}" for m in members)
    return IntelAnswer(
        "succeeded",
        f"Tactic '{tactic}' in MITRE ATT&CK ({_as_of(attack, 'ATT&CK')}), {len(members)} techniques: {listed}. "
        "Look up a technique id for its detection strategies and mitigations.",
    )
