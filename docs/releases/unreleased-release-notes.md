# Release Notes - Unreleased (draft)

**Release Date**: not yet released  
**Type**: Feature / Deployment  
**Scope**: Multiple workers on one host (ARC-01), quotas counted once across workers, clarification fix, dead-code cleanup

> This is a draft. The version number is decided at release time; until then this
> file is the upgrade guide for whatever is merged to `main` after v0.7.0.3.

---

## Overview

Until this release the backend kept its limits, approvals, execution streams, session
writes and ingestion jobs in each process's memory, so it could only run as one
worker. Starting a second worker made logins count per worker, approval tokens fail
on the worker that did not issue them, SSE subscriptions return 404 and concurrent
session writes lose messages.

This release moves every piece of state that the workers must agree on out of the
process. The production stack now runs several workers by default.

---

## Key Highlights

### 1. Shared state (Redis and SQLite)

- Login, registration and upload limits, the query guard and OAuth state live in
  Redis. With `STATE_BACKEND=shared`, a Redis outage answers **503 with `Retry-After`**
  instead of silently falling back to per-process counting.
- Approval tokens, governed-tool audit records and admin one-time-token use are
  SQLite tables, independent of Redis.
- Execution events and answer drafts are one Redis stream per execution, so an SSE
  subscription can land on any worker.
- Session history and session metadata are written in SQLite transactions.

### 2. Queued ingestion

- Uploads and reindexing are queued (RQ) and executed by a single `ingest-worker`;
  Chroma runs as a server. Reindex returns **202**.
- Every write to the document index holds one cross-process lock. A request that
  cannot get it within `INDEX_LOCK_REQUEST_TIMEOUT_SECONDS` gets **503 `INDEX_BUSY`**
  with `Retry-After`; nothing was changed, and a refused upload does not spend the
  upload quota.

### 3. Consistency and operations across workers

- A change to the corpus, the configuration or the model settings on one worker is
  applied by every other worker on its next request.
- SQLite schemas are created and upgraded by versioned migrations; migrations, the
  first administrator and one-time cleanup run once, in an `init` service.
- `/metrics` uses Prometheus multiprocess mode and sums every worker; log levels set
  from the admin console reach every worker; per-worker admin views show the pid.
- gunicorn replaces a worker whose event loop stops responding for
  `GUNICORN_TIMEOUT_SECONDS`.
- Client addresses are taken only from the trusted reverse proxy
  (`QUERYMIND_TRUSTED_PROXIES`, the compose network's `QUERYMIND_SUBNET`).

### 4. Quotas

- The per-minute query and web-search quotas (`QUOTA_ENABLED`, `QUOTA_MODE`,
  `QUOTA_QUERY_MAX_PER_MINUTE`, `QUOTA_WEB_MAX_PER_MINUTE`) are enforced, and counted
  once for all workers. An exhausted query quota answers **429**. `QUOTA_ENABLED=true`
  in the production layer.

### 5. Fixes and cleanup

- Clarification recognises a component, data source or scenario written in English
  directly next to Chinese text (`neo4j报错`, `数据源是mysql数据`) instead of asking for it.
- Session export no longer takes `include_context`, and import no longer returns
  `context_imported`: the option always exported nothing. Older clients that still
  send the field are ignored rather than refused, and older export files still import.
- Unused code removed: a second, uncalled streaming path, uncalled session import
  helpers and the last unreachable functions.

---

## Upgrade

```bash
# 1. Stop the old stack first. Never pass -v: it deletes the data volumes.
docker compose -f deploy/compose/compose.yaml down

# 2. Deploy as usual.
./deploy/scripts/deploy.sh production balanced
```

- **Why `down` first**: the compose network now has a fixed subnet, and containers
  whose own configuration did not change would otherwise keep pointing at the old
  network.
- **Redis and the Chroma server are required** in the compose stack, because it
  defaults to `STATE_BACKEND=shared`.
- **Data migration is automatic**: the `init` service moves file-based sessions to
  SQLite and the embedded Chroma directory to the Chroma server, reads both back, and
  exits non-zero (keeping the backend down) if verification fails. Original files
  are not deleted, and the step is skipped on later deploys.
- **Outside the image**, keep `APP_WORKERS` in step with the worker count you start:
  a hand-run `uvicorn --workers N` with `APP_WORKERS` unset is not detected.

### New settings

| Setting | Default | Notes |
| --- | --- | --- |
| `STATE_BACKEND` | `memory` (app), `shared` (compose) | `shared` requires Redis, `HISTORY_BACKEND=sqlite`, `SESSION_METADATA_BACKEND=database` and `CHROMA_SERVER_URL` |
| `APP_WORKERS` | `1` (2 in the production layer) | startup refuses `>1` unless `STATE_BACKEND=shared` |
| `CHROMA_SERVER_URL` | unset | required in shared mode |
| `STATE_KEY_PREFIX` | `qm:` | Redis key prefix for shared state |
| `INDEX_LOCK_REQUEST_TIMEOUT_SECONDS` | `5` | how long a request waits for the index lock |
| `QUOTA_*` | see above | per-minute query and web-search quotas |
| `QUERYMIND_TRUSTED_PROXIES`, `QUERYMIND_SUBNET` | compose network | reverse-proxy trust |
| `GUNICORN_TIMEOUT_SECONDS` | `60` | worker replacement on a stalled event loop |

### API changes

- `POST` reindex returns **202** and completes asynchronously.
- Document writes can answer **503 `INDEX_BUSY`** with `Retry-After`.
- With `STATE_BACKEND=shared`, routes that depend on shared state answer **503** with
  `Retry-After` while Redis is unavailable.
- An exhausted query quota answers **429**.
- `POST /api/v1/sessions/{id}/export` ignores `include_context`; the import response
  has no `context_imported`.

### Rollback

Set `STATE_BACKEND=memory` and `APP_WORKERS=1` to return to the single-process
behaviour. The migration never deletes the original session files or the embedded
Chroma directory, but it does not keep them up to date either: keep
`HISTORY_BACKEND=sqlite` so sessions written after the upgrade stay visible, and
note that documents indexed after the upgrade exist only in the Chroma server.
Either keep `CHROMA_SERVER_URL` set or reindex after rolling back.

---

## Verification

```bash
# Backend, as CI runs it
make test-ci

# Multi-process suite against a real Redis and Chroma server
make up
QM_INTEGRATION_REDIS_URL=redis://:PASSWORD@127.0.0.1:6379/0 \
QM_INTEGRATION_CHROMA_URL=http://127.0.0.1:8001 \
pytest tests/integration/multiworker -q

# Frontend
cd frontend && npm test -- --run
```

Measured before release: Windows `make test-ci` 3,483 passed / 15 skipped; CI (Linux,
Python 3.11, with Redis and Chroma service containers) 3,498 passed; `vitest` 232
passed; multi-process suite 10 passed against Redis 7.4.1 and Chroma 1.5.9.
