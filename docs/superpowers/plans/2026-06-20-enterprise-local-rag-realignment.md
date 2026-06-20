# Enterprise Local RAG Realignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-center the repository around a stable enterprise local-first RAG platform, reduce scope drift, and restore trust in release status, versioning, and verification.

**Architecture:** Treat the realignment as a product-hardening slice rather than a feature sprint. First establish a single source of truth for product positioning and version state, then split stable and experimental surfaces, then harden the default validation path so the repository can honestly claim a smaller but reliable enterprise baseline.

**Tech Stack:** FastAPI, React/Vite, Pydantic settings, pytest, Markdown docs, release/version metadata, CI quality gate scripts

---

## File Structure

- Create: `docs/project/ENTERPRISE_LOCAL_RAG_DIRECTION.md`
  - One-page product contract for the stable product line: target user, core workflows, success criteria, non-goals, and explicit experimental surfaces.

- Create: `docs/project/ENTERPRISE_LOCAL_RAG_ROADMAP.md`
  - 7/30/90-day roadmap anchored to stable enterprise outcomes instead of feature expansion.

- Create: `tests/test_version_consistency.py`
  - Enforce that `VERSION`, `pyproject.toml`, `app/__version__.py`, and README release references do not drift.

- Modify: `README.md`
  - Rewrite the opening narrative around the enterprise local RAG baseline.
  - Move graph/evaluation/advanced-RAG capabilities into an explicitly marked experimental section.

- Modify: `CHANGELOG.md`
  - Add a top-level unreleased or recovery entry that explains the realignment and links to corrected release status.

- Modify: `VERSION`
- Modify: `app/__version__.py`
- Modify: `pyproject.toml`
  - Align all version sources to one agreed current version before any further release note work.

- Modify: `scripts/ci_quality_gate.py`
  - Separate stable checks from runtime-dependent or experimental checks.

- Modify: `Makefile`
  - Add explicit stable and full validation commands.

- Modify: `tests/conftest.py`
  - Introduce shared pytest markers or skip helpers for runtime-bound suites.

- Modify: `tests/test_chinese_bm25.py`
  - Fix the collection-blocking `_jieba_available` reference and keep Chinese retrieval checks inside the stable baseline.

- Modify: `tests/integration/test_streaming_pdf.py`
  - Convert hard import failures into clean skips when dev-only document tooling is absent.

- Modify: `docs/releases/RELEASE_NOTES_v0.4.6.md`
  - Replace promotional wording with corrected release status and link forward to the realignment plan.

- Modify: `docs/project/production_readiness_checklist.md`
  - Re-scope readiness to the stable enterprise baseline only.

- Modify: `docs/project/next-actions.md`
  - Replace feature-expansion next steps with enterprise-baseline recovery actions.

---

### Task 1: Freeze the stable product contract

**Files:**
- Create: `docs/project/ENTERPRISE_LOCAL_RAG_DIRECTION.md`
- Modify: `README.md`
- Modify: `docs/project/next-actions.md`

- [ ] Write a one-page direction doc that defines the stable product as: secure document ingestion, grounded retrieval, sessioned chat, admin governance, and operational visibility.
- [ ] Add a short "Not in stable scope" section listing graph enrichment, evaluation lab features, agent visualization, and advanced reasoning endpoints as experimental by default.
- [ ] Rewrite the README summary so the first screen describes the stable baseline first and moves stretch capabilities into an "Experimental and optional" section.
- [ ] Replace the current next-actions list with baseline recovery work: version truth, stable CI, release honesty, and enterprise smoke coverage.

### Task 2: Restore version truth and release credibility

**Files:**
- Modify: `VERSION`
- Modify: `app/__version__.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/releases/RELEASE_NOTES_v0.4.6.md`
- Create: `tests/test_version_consistency.py`

- [ ] Pick one canonical current version and update all version-bearing files to match before any new release claims are written.
- [ ] Add a short recovery section at the top of `CHANGELOG.md` explaining that release metadata is being re-synchronized after drift between `0.4.3`, `0.4.4`, and `0.4.6`.
- [ ] Update `docs/releases/RELEASE_NOTES_v0.4.6.md` so it no longer stands alone as a success narrative and instead references the corrected status and unresolved follow-up work.
- [ ] Add a focused pytest file that reads `VERSION`, `pyproject.toml`, `app/__version__.py`, and README release text and fails when they disagree.

Suggested test skeleton for `tests/test_version_consistency.py`:

```python
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_version_files_match():
    version_txt = _read("VERSION").strip()
    pyproject = _read("pyproject.toml")
    package = _read("app/__version__.py")

    pyproject_version = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    package_version = re.search(r'__version__ = "([^"]+)"', package).group(1)

    assert version_txt == pyproject_version == package_version
```

### Task 3: Split stable validation from experimental validation

**Files:**
- Modify: `scripts/ci_quality_gate.py`
- Modify: `Makefile`
- Modify: `tests/conftest.py`
- Modify: `docs/project/production_readiness_checklist.md`

- [ ] Define a stable validation lane that only requires the enterprise baseline: auth, documents, query, sessions, admin safety, and core retrieval.
- [ ] Define a full validation lane for Redis, Ollama, Neo4j, evaluation datasets, and optional advanced features.
- [ ] Add shared pytest markers such as `stable`, `runtime`, and `experimental` so collection and CI intent are explicit.
- [ ] Update the production readiness checklist so "production-ready" only means the stable lane passes and all accepted risks are documented.

Suggested `Makefile` additions:

```makefile
test-stable:
	pytest -q -m "stable and not runtime and not experimental"

test-full:
	pytest -q

quality-gate-stable:
	python scripts/ci_quality_gate.py --mode stable --report-md artifacts/quality-report-stable.md
```

### Task 4: Remove validation blockers from the stable path

**Files:**
- Modify: `tests/test_chinese_bm25.py`
- Modify: `tests/integration/test_streaming_pdf.py`
- Modify: `README.md`

- [ ] Fix the `_jieba_available` NameError so the suite can collect cleanly on the default path.
- [ ] Change the streaming-PDF integration test to use `pytest.importorskip("reportlab")` or an equivalent fixture-based skip instead of crashing collection when dev extras are absent.
- [ ] Ensure the README test instructions clearly separate `pip install -e .` from `pip install -e ".[dev]"`, and state which command is required for the stable test lane.
- [ ] Re-run `pytest -q -m stable` and confirm the stable lane can fail only on real assertions, not environment or collection noise.

Suggested import guard for `tests/integration/test_streaming_pdf.py`:

```python
import pytest


reportlab = pytest.importorskip("reportlab")
```

### Task 5: Fence experimental product surfaces behind explicit language

**Files:**
- Modify: `README.md`
- Modify: `docs/project/ENTERPRISE_LOCAL_RAG_DIRECTION.md`
- Modify: `docs/project/production_readiness_checklist.md`
- Modify: `docs/releases/RELEASE_NOTES_v0.4.6.md`

- [ ] Add an "Experimental" label to evaluation, advanced-RAG, graph-heavy reasoning, and agent-visualization features anywhere they are advertised.
- [ ] Remove any language that implies these surfaces are part of the default supported production baseline.
- [ ] Document re-entry criteria for experiments: stable owner, measurable value, test coverage, and a defined rollback story.
- [ ] Make the release notes explicit that experimental capability breadth is not the same as production readiness.

### Task 6: Publish the 7/30/90-day enterprise roadmap

**Files:**
- Create: `docs/project/ENTERPRISE_LOCAL_RAG_ROADMAP.md`
- Modify: `docs/project/next-actions.md`

- [ ] Write a 7-day recovery plan focused on version truth, corrected release notes, stable CI markers, and collection-clean tests.
- [ ] Write a 30-day hardening plan focused on the enterprise core loop: login, upload, index, query, cite, audit, and rollback.
- [ ] Write a 90-day plan focused on measured re-introduction of optional graph, evaluation, and advanced-reasoning features behind explicit flags and owners.
- [ ] Keep roadmap success metrics operational: stable test pass rate, smoke pass rate, release-note drift incidents, and production-readiness sign-off completeness.

Suggested roadmap outline:

```markdown
## 7 Days
- Align versions and release notes
- Make stable test lane green
- Rewrite README and direction docs

## 30 Days
- Lock enterprise smoke flows
- Add baseline dashboards and release checklist discipline
- Freeze new experimental feature merges unless they are flag-gated

## 90 Days
- Re-introduce only experiments with owner, KPI, and rollback
- Publish supported-vs-experimental capability matrix
- Prepare the first honestly scoped enterprise release
```

---

## Definition of Done

- Stable product positioning is documented in one place and reflected in README.
- Version metadata no longer disagrees across repository entry points.
- Stable validation is a first-class command path and does not fail during test collection for avoidable reasons.
- Release notes stop over-claiming and point to corrected status when work is incomplete.
- The roadmap prioritizes enterprise baseline reliability over feature breadth.
