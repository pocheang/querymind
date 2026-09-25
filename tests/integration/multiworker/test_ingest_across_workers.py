"""Uploads to both workers at once end up indexed once, and the two indexes agree (ARC-01 phase 10, scenario 5).

Every write to the document index holds one cross-process lock, ingestion runs
in the single ingest worker, and the vectors live in the Chroma server. Ten
uploads split across the two API workers, all in flight together, must leave
the corpus file and the Chroma collection with the same chunks -- counted, and
compared by id -- and every document ready.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from multiworker_stack import Stack, build_stack

# The first test of a module includes starting the stack (init, an ingest worker,
# two API processes), and scenario 7 waits out a 40-second lease; CI's 120s
# per-test hang detector is sized for unit tests.
pytestmark = pytest.mark.timeout(300)

DOCUMENTS = 10


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    yield from build_stack(tmp_path_factory.mktemp("ingest"), RATE_LIMIT_ENABLED="false")


def _text(n: int) -> str:
    # Distinct content per file: identical bytes would be deduplicated, which is
    # a different property from the one under test.
    paragraph = f"Document {n} describes retention rule {n}: records of type R{n} are kept for {30 + n} days. "
    return (paragraph * 40).strip()


def _corpus_records(stack: Stack) -> list[dict]:
    path = stack.root / "data" / "chunks" / "chunks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _wait_until_ready(client, expected: int, timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    report: dict = {}
    while time.monotonic() < deadline:
        report = client.get("/documents/index-health").json()
        if report["ready_documents"] + report["failed_documents"] >= expected and not report["indexing_documents"]:
            return report
        time.sleep(0.5)
    raise AssertionError(
        f"not indexed after {timeout}s: {report and {k: v for k, v in report.items() if k != 'documents'}}"
    )


def test_concurrent_uploads_to_both_workers_agree_in_the_corpus_and_in_chroma(stack):
    clients = [stack.login(worker) for worker in stack.workers]

    busy = []

    def upload(n: int):
        """As a client should: an upload that meets a held index lock is refused whole, and retried."""

        files = {"files": (f"retention_{n}.txt", _text(n).encode("utf-8"), "text/plain")}
        for _ in range(30):
            response = clients[n % 2].post("/upload", files=files)
            if response.status_code != 503:
                return response
            assert response.json()["error_code"] == "INDEX_BUSY", response.text
            busy.append(n)
            time.sleep(float(response.headers.get("Retry-After", "1")))
        return response

    with ThreadPoolExecutor(max_workers=DOCUMENTS) as pool:
        responses = list(pool.map(upload, range(DOCUMENTS)))

    assert [r.status_code for r in responses] == [200] * DOCUMENTS, [
        r.text[:200] for r in responses if r.status_code != 200
    ]
    # Not an assertion about the count, which depends on timing, but it has to
    # be recorded: a 503 must have changed nothing, and the checks below are
    # what prove it did not.
    print(f"uploads refused with INDEX_BUSY and retried: {len(busy)}")
    report = _wait_until_ready(clients[0], DOCUMENTS)
    assert (report["ready_documents"], report["failed_documents"]) == (DOCUMENTS, 0)

    records = _corpus_records(stack)
    from app.retrievers.stores.vector import chroma_http_client

    # MODEL_BACKEND=local writes to `<CHROMA_COLLECTION>_local` (get_vector_store).
    collection = chroma_http_client(stack.chroma_url).get_collection(f"{stack.collection}_local")
    stored = collection.get(include=[])["ids"]

    assert len(records) == report["total_chunks"] > DOCUMENTS
    assert len(stored) == len(records)
    record_ids = {record.get("chunk_id") or record.get("id") for record in records}
    assert set(stored) == record_ids
    sources = {str(record.get("metadata", {}).get("source", "")).rsplit("/", 1)[-1] for record in records}
    assert {f"retention_{n}.txt" for n in range(DOCUMENTS)} <= {s.rsplit("\\", 1)[-1] for s in sources}
