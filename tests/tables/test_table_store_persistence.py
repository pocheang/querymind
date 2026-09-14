"""SQL-queryable tables outlive the process that ingested them.

The first version held every table in one process's memory: a restart emptied
the store, and with several workers a table was queryable only on the worker
that happened to ingest it -- so the same question answered on one request and
"not found" on the next. Tables now live in the application database, and the
engines are a cache over it.

What makes a cache safe here is that ownership and version are read from the
database on every call. Two stores over one file stand in for two workers, or
for a process before and after a restart.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.multimodal.models import TableContent
from app.services.tables import store as store_module
from app.services.tables.store import TableStore


def _table(table_id: str, rows: list[list[str]]) -> TableContent:
    return TableContent(
        table_id=table_id,
        doc_id=f"doc-{table_id}",
        page_number=1,
        headers=["Region", "Sales"],
        rows=rows,
        summary="",
        metadata={"sheet": "Q1"},
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "app.db"


def test_a_table_survives_a_restart(db_path: Path) -> None:
    TableStore(prefer_duckdb=False, db_path=db_path).save_table(
        "acme", _table("sales", [["North", "1000"], ["South", "2000"]]), owner_user_id="alice", source="u/a/s.xlsx"
    )

    restarted = TableStore(prefer_duckdb=False, db_path=db_path)
    res = restarted.query_table("acme", "sales", "SELECT SUM(sales) FROM table", user_id="alice")

    assert res.error is None
    assert res.rows[0][0] == 3000
    assert restarted.get_table("acme", "sales", user_id="alice").metadata == {"sheet": "Q1"}


def test_ownership_is_persisted_with_the_rows(db_path: Path) -> None:
    TableStore(prefer_duckdb=False, db_path=db_path).save_table(
        "acme", _table("private", [["North", "1"]]), owner_user_id="alice"
    )

    other_worker = TableStore(prefer_duckdb=False, db_path=db_path)

    assert other_worker.get_schema("acme", "private", user_id="bob") is None
    assert other_worker.get_schema("acme", "private", user_id="alice") is not None


def test_a_deletion_on_one_worker_is_seen_by_another_that_had_it_cached(db_path: Path) -> None:
    """The failure a cache invites: worker B keeps serving a table worker A deleted."""
    worker_a = TableStore(prefer_duckdb=False, db_path=db_path)
    worker_b = TableStore(prefer_duckdb=False, db_path=db_path)
    worker_a.save_table("acme", _table("t", [["North", "1"]]), owner_user_id="alice", source="u/a/t.xlsx")
    assert worker_b.get_schema("acme", "t", user_id="alice") is not None  # now cached on B

    assert worker_a.delete_by_sources(["u/a/t.xlsx"]) == 1

    assert worker_b.get_schema("acme", "t", user_id="alice") is None
    res = worker_b.query_table("acme", "t", "SELECT * FROM table", user_id="alice")
    assert res.error is not None and "not found" in res.error


def test_a_reingest_on_one_worker_replaces_what_another_had_cached(db_path: Path) -> None:
    worker_a = TableStore(prefer_duckdb=False, db_path=db_path)
    worker_b = TableStore(prefer_duckdb=False, db_path=db_path)
    worker_a.save_table("acme", _table("t", [["North", "1"]]), owner_user_id="alice")
    assert worker_b.query_table("acme", "t", "SELECT SUM(sales) FROM table", user_id="alice").rows[0][0] == 1

    worker_a.save_table("acme", _table("t", [["North", "1"], ["South", "41"]]), owner_user_id="alice")

    assert worker_b.query_table("acme", "t", "SELECT SUM(sales) FROM table", user_id="alice").rows[0][0] == 42


def test_an_evicted_engine_is_rebuilt_from_the_database(db_path: Path) -> None:
    store = TableStore(prefer_duckdb=False, db_path=db_path, max_cached_engines=1)
    store.save_table("acme", _table("first", [["North", "7"]]), owner_user_id="alice")
    store.save_table("acme", _table("second", [["South", "9"]]), owner_user_id="alice")  # evicts "first"

    res = store.query_table("acme", "first", "SELECT SUM(sales) FROM table", user_id="alice")

    assert res.error is None and res.rows[0][0] == 7


def test_the_test_run_never_persists_into_the_developer_database(monkeypatch) -> None:
    """Same rule as the admin bootstrap: under pytest the shared store is in memory."""
    monkeypatch.setattr(store_module, "_GLOBAL_TABLE_STORE", None)

    assert os.getenv("PYTEST_CURRENT_TEST")
    assert store_module.get_table_store().persistent is False
