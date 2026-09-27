"""Turn the four public feeds into validated rows. Pure functions: no I/O, no clock.

Every field that reaches a tool summary is checked here, because a tool result is
cited as authoritative: a CVE id that is not one, a score outside 0-10 or a date
that does not parse is dropped and counted rather than stored and repeated. What
is NOT kept matters as much:

- NVD's `descriptions` are third-party prose. They are not stored at all, so no
  tool can put them into a model's context (plan 2.3).
- ATT&CK descriptions are MITRE's own text, used with attribution, and kept only
  to their first sentence with the `(Citation: ...)` markers removed.
- Only `vulnerable: true` CPE matches are kept: a `false` match names the
  platform a vulnerability needs (e.g. a JDK version), not an affected product.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime

__all__ = [
    "AttackBundle",
    "AttackDetection",
    "AttackMitigation",
    "AttackTechnique",
    "CpeRange",
    "CveRecord",
    "EpssRecord",
    "KevRecord",
    "ParseResult",
    "parse_attack_bundle",
    "parse_epss_csv",
    "parse_kev",
    "parse_nvd_page",
]

CVE_ID = re.compile(r"CVE-\d{4}-\d{4,7}\Z")
TECHNIQUE_ID = re.compile(r"T\d{4}(?:\.\d{3})?\Z")
MITIGATION_ID = re.compile(r"M\d{4}\Z")
_CITATION = re.compile(r"\(Citation: [^)]{0,200}\)")


@dataclass(frozen=True)
class ParseResult:
    """Rows that passed, and how many were dropped -- a feed that drops half its rows is news."""

    rows: tuple
    rejected: int = 0


# --- NVD CVE API 2.0 ----------------------------------------------------------------


@dataclass(frozen=True)
class CpeRange:
    vendor: str
    product: str
    version: str  # "*" when the range fields carry the bounds
    start_including: str = ""
    start_excluding: str = ""
    end_including: str = ""
    end_excluding: str = ""


@dataclass(frozen=True)
class CveRecord:
    cve_id: str
    published: str
    last_modified: str
    status: str
    cvss_version: str
    cvss_score: float | None
    cvss_vector: str
    severity: str
    cvss_source: str
    cwe: tuple[str, ...]
    ranges: tuple[CpeRange, ...] = field(default_factory=tuple)


def parse_nvd_page(payload: dict) -> ParseResult:
    rows: list[CveRecord] = []
    rejected = 0
    for vulnerability in payload.get("vulnerabilities") or ():
        record = _nvd_record((vulnerability or {}).get("cve") or {})
        if record is None:
            rejected += 1
        else:
            rows.append(record)
    return ParseResult(tuple(rows), rejected)


def _nvd_record(cve: dict) -> CveRecord | None:
    cve_id = str(cve.get("id") or "").upper()
    published = _iso_datetime(cve.get("published"))
    last_modified = _iso_datetime(cve.get("lastModified"))
    if not CVE_ID.match(cve_id) or not published or not last_modified:
        return None
    version, score, vector, severity, source = _cvss_fields(_primary_cvss(cve.get("metrics") or {}))
    return CveRecord(
        cve_id=cve_id,
        published=published,
        last_modified=last_modified,
        status=str(cve.get("vulnStatus") or "")[:40],
        cvss_version=version,
        cvss_score=score,
        cvss_vector=vector,
        severity=severity,
        cvss_source=source,
        cwe=_weaknesses(cve.get("weaknesses") or ()),
        ranges=tuple(_ranges(cve.get("configurations") or ())),
    )


def _cvss_fields(metric: dict | None) -> tuple[str, float | None, str, str, str]:
    """(version, score, vector, severity, source) -- all empty when there is no valid score.

    A vector or severity without the score it belongs to would be a claim with
    nothing under it, so they go together or not at all.
    """

    metric = metric or {}
    data = metric.get("cvssData") or {}
    score = _score(data.get("baseScore"))
    if score is None:
        return "", None, "", "", ""
    return (
        str(data.get("version") or "")[:8],
        score,
        str(data.get("vectorString") or "")[:200],
        str(data.get("baseSeverity") or metric.get("baseSeverity") or "").upper()[:16],
        str(metric.get("source") or "")[:120],
    )


# Newest CVSS first; within a version, NVD's own (Primary) score first. Mixing
# sources without saying which is exactly how the curated table came to carry
# Citrix's 9.4 where NVD has 7.5 -- the source is stored beside the score.
_CVSS_KEYS = ("cvssMetricV31", "cvssMetricV30", "cvssMetricV40", "cvssMetricV2")


def _primary_cvss(metrics: dict) -> dict | None:
    for key in _CVSS_KEYS:
        entries = [entry for entry in metrics.get(key) or () if isinstance(entry, dict)]
        if entries:
            return next((entry for entry in entries if entry.get("type") == "Primary"), entries[0])
    return None


def _weaknesses(weaknesses) -> tuple[str, ...]:
    found: list[str] = []
    for weakness in weaknesses:
        for description in (weakness or {}).get("description") or ():
            value = str((description or {}).get("value") or "")
            if re.fullmatch(r"CWE-\d{1,5}", value) and value not in found:
                found.append(value)
    return tuple(found[:10])


def _ranges(configurations) -> list[CpeRange]:
    matches = (
        match or {}
        for configuration in configurations
        for node in (configuration or {}).get("nodes") or ()
        for match in (node or {}).get("cpeMatch") or ()
    )
    found = (_cpe_range(match) for match in matches)
    return list(dict.fromkeys(cpe_range for cpe_range in found if cpe_range is not None))


def _cpe_range(match: dict) -> CpeRange | None:
    if match.get("vulnerable") is not True:
        return None
    parts = str(match.get("criteria") or "").split(":")
    # cpe:2.3:part:vendor:product:version:...
    if len(parts) < 6 or parts[0] != "cpe" or parts[1] != "2.3":
        return None
    vendor, product, version = parts[3].lower(), parts[4].lower(), parts[5]
    if not vendor or not product or vendor == "*" or product == "*":
        return None
    return CpeRange(
        vendor=vendor[:120],
        product=product[:160],
        version=version[:60],
        start_including=str(match.get("versionStartIncluding") or "")[:60],
        start_excluding=str(match.get("versionStartExcluding") or "")[:60],
        end_including=str(match.get("versionEndIncluding") or "")[:60],
        end_excluding=str(match.get("versionEndExcluding") or "")[:60],
    )


# --- CISA KEV --------------------------------------------------------------------------


@dataclass(frozen=True)
class KevRecord:
    cve_id: str
    vendor: str
    product: str
    name: str
    date_added: str
    due_date: str
    known_ransomware: str
    required_action: str


def parse_kev(payload: dict) -> ParseResult:
    rows: list[KevRecord] = []
    rejected = 0
    for entry in payload.get("vulnerabilities") or ():
        entry = entry or {}
        cve_id = str(entry.get("cveID") or "").upper()
        added = _iso_date(entry.get("dateAdded"))
        if not CVE_ID.match(cve_id) or not added:
            rejected += 1
            continue
        rows.append(
            KevRecord(
                cve_id=cve_id,
                vendor=str(entry.get("vendorProject") or "")[:120],
                product=str(entry.get("product") or "")[:160],
                name=str(entry.get("vulnerabilityName") or "")[:240],
                date_added=added,
                due_date=_iso_date(entry.get("dueDate")) or "",
                known_ransomware=str(entry.get("knownRansomwareCampaignUse") or "")[:16],
                required_action=str(entry.get("requiredAction") or "")[:400],
            )
        )
    return ParseResult(tuple(rows), rejected)


# --- FIRST EPSS --------------------------------------------------------------------------


@dataclass(frozen=True)
class EpssRecord:
    cve_id: str
    score: float
    percentile: float


_SCORE_DATE = re.compile(r"score_date:(\d{4}-\d{2}-\d{2})")


def parse_epss_csv(text: str) -> tuple[str, ParseResult]:
    """The feed's own score date, and its rows. A feed without a score date is refused.

    The date is the only thing that says how current a probability is, and a
    probability without one is not something a reader can weigh.
    """

    first_line, _, rest = text.partition("\n")
    match = _SCORE_DATE.search(first_line)
    if not match or not _iso_date(match.group(1)):
        raise ValueError("EPSS feed carries no score_date in its first line")
    rows: list[EpssRecord] = []
    rejected = 0
    for row in csv.DictReader(io.StringIO(rest)):
        cve_id = str(row.get("cve") or "").upper()
        score, percentile = _probability(row.get("epss")), _probability(row.get("percentile"))
        if not CVE_ID.match(cve_id) or score is None or percentile is None:
            rejected += 1
            continue
        rows.append(EpssRecord(cve_id, score, percentile))
    return match.group(1), ParseResult(tuple(rows), rejected)


# --- MITRE ATT&CK (STIX 2.1 bundle) ---------------------------------------------------


@dataclass(frozen=True)
class AttackTechnique:
    technique_id: str
    name: str
    tactics: tuple[str, ...]
    is_subtechnique: bool
    parent_id: str
    platforms: tuple[str, ...]
    url: str
    summary: str
    revoked: bool
    deprecated: bool


@dataclass(frozen=True)
class AttackMitigation:
    technique_id: str
    mitigation_id: str
    name: str


@dataclass(frozen=True)
class AttackDetection:
    technique_id: str
    strategy_id: str
    name: str


@dataclass(frozen=True)
class AttackBundle:
    version: str
    modified: str
    techniques: tuple[AttackTechnique, ...]
    mitigations: tuple[AttackMitigation, ...]
    detections: tuple[AttackDetection, ...]
    rejected: int


def parse_attack_bundle(bundle: dict) -> AttackBundle:
    """Techniques with their mitigations and detection strategies.

    Detection moved out of the technique in ATT&CK v18+: `x_mitre_detection` is
    empty and `x-mitre-detection-strategy` objects point at techniques through
    `detects` relationships. Reading only the technique would report no
    detection guidance for anything.
    """

    objects = [obj for obj in bundle.get("objects") or () if isinstance(obj, dict)]
    techniques, rejected = _techniques(objects)
    parents = _parents(objects, techniques)
    mitigations, detections = _links(objects, techniques)
    collection = next((obj for obj in objects if obj.get("type") == "x-mitre-collection"), {})
    return AttackBundle(
        version=str(collection.get("x_mitre_version") or "")[:16],
        modified=str(collection.get("modified") or "")[:40],
        techniques=tuple(
            technique if technique.technique_id not in parents else _with_parent(technique, parents)
            for technique in techniques.values()
        ),
        mitigations=tuple(dict.fromkeys(mitigations)),
        detections=tuple(dict.fromkeys(detections)),
        rejected=rejected,
    )


def _live(obj: dict) -> bool:
    return not (obj.get("revoked") or obj.get("x_mitre_deprecated"))


def _links(
    objects: list[dict], techniques: dict[str, AttackTechnique]
) -> tuple[list[AttackMitigation], list[AttackDetection]]:
    """Mitigations and detection strategies attached to techniques, both ends current."""

    by_stix = {str(obj.get("id")): obj for obj in objects}
    mitigations: list[AttackMitigation] = []
    detections: list[AttackDetection] = []
    for relationship in (obj for obj in objects if obj.get("type") == "relationship" and _live(obj)):
        target = techniques.get(str(relationship.get("target_ref")))
        source = by_stix.get(str(relationship.get("source_ref"))) or {}
        if target is None or not _live(source):
            continue
        link = _link(relationship.get("relationship_type"), source, target.technique_id)
        if isinstance(link, AttackMitigation):
            mitigations.append(link)
        elif isinstance(link, AttackDetection):
            detections.append(link)
    return mitigations, detections


def _link(kind, source: dict, technique_id: str) -> AttackMitigation | AttackDetection | None:
    name = str(source.get("name") or "")
    if kind == "mitigates" and source.get("type") == "course-of-action":
        mitigation_id = _external_id(source) or ""
        return AttackMitigation(technique_id, mitigation_id, name[:200]) if MITIGATION_ID.match(mitigation_id) else None
    if kind == "detects" and source.get("type") == "x-mitre-detection-strategy":
        return AttackDetection(technique_id, _external_id(source) or "", name[:240])
    return None


def _techniques(objects: list[dict]) -> tuple[dict[str, AttackTechnique], int]:
    techniques: dict[str, AttackTechnique] = {}
    rejected = 0
    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue
        technique_id = _external_id(obj)
        if not technique_id or not TECHNIQUE_ID.match(technique_id):
            rejected += 1
            continue
        techniques[str(obj.get("id"))] = AttackTechnique(
            technique_id=technique_id,
            name=str(obj.get("name") or "")[:200],
            tactics=tuple(
                str(phase.get("phase_name"))
                for phase in obj.get("kill_chain_phases") or ()
                if (phase or {}).get("kill_chain_name") == "mitre-attack" and phase.get("phase_name")
            ),
            is_subtechnique=bool(obj.get("x_mitre_is_subtechnique")),
            parent_id=technique_id.split(".")[0] if "." in technique_id else "",
            platforms=tuple(str(p)[:40] for p in obj.get("x_mitre_platforms") or ())[:20],
            url=_external_url(obj),
            summary=_first_sentence(str(obj.get("description") or "")),
            revoked=bool(obj.get("revoked")),
            deprecated=bool(obj.get("x_mitre_deprecated")),
        )
    return techniques, rejected


def _parents(objects: list[dict], technique_by_stix: dict[str, AttackTechnique]) -> dict[str, str]:
    """Sub-technique -> parent id, from `subtechnique-of`, falling back to the id's own prefix."""

    parents: dict[str, str] = {}
    for obj in objects:
        if obj.get("type") == "relationship" and obj.get("relationship_type") == "subtechnique-of":
            child = technique_by_stix.get(str(obj.get("source_ref")))
            parent = technique_by_stix.get(str(obj.get("target_ref")))
            if child and parent:
                parents[child.technique_id] = parent.technique_id
    return parents


def _with_parent(technique: AttackTechnique, parents: dict[str, str]) -> AttackTechnique:
    from dataclasses import replace

    return replace(technique, parent_id=parents[technique.technique_id])


def _external_id(obj: dict) -> str | None:
    for reference in obj.get("external_references") or ():
        if (reference or {}).get("source_name") == "mitre-attack" and reference.get("external_id"):
            return str(reference["external_id"])
    return None


def _external_url(obj: dict) -> str:
    for reference in obj.get("external_references") or ():
        url = str((reference or {}).get("url") or "")
        if (reference or {}).get("source_name") == "mitre-attack" and url.startswith("https://attack.mitre.org/"):
            return url[:200]
    return ""


def _first_sentence(text: str) -> str:
    """The first sentence, citations removed, at most 300 characters.

    Split by hand rather than with a sentence regex: a pattern like
    `(.+?)\\.\\s` is the adjacent-quantifier shape this repository keeps
    finding to be super-linear on long input.
    """

    cleaned = " ".join(_CITATION.sub("", text).split())
    end = cleaned.find(". ")
    sentence = cleaned if end < 0 else cleaned[: end + 1]
    return sentence[:300]


# --- shared validation --------------------------------------------------------------------


def _iso_datetime(value) -> str:
    text = str(value or "")
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return ""
    return text[:32]


def _iso_date(value) -> str:
    text = str(value or "")[:10]
    try:
        date.fromisoformat(text)
    except ValueError:
        return ""
    return text


def _score(value) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return score if 0.0 <= score <= 10.0 else None


def _probability(value) -> float | None:
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    return probability if 0.0 <= probability <= 1.0 else None
