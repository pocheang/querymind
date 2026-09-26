"""Two real API processes, one ingest worker, one Redis and one Chroma server (ARC-01 phases 0 and 10).

Imported by the test modules beside it (tests are not a package here, so a
uniquely named module rather than conftest.py). `conftest.py` holds the default
`stack` fixture; a module needing different settings builds its own.

The stack is the deployment's shape without its containers: `python -m
app.init_app` runs to completion first (migrations, the first administrator),
then one `python -m app.ingest_worker`, then two uvicorn processes on their own
ports -- STATE_BACKEND=shared, sqlite history, database metadata, a Chroma
server. Everything they agree on has to cross a process boundary, which is the
only thing these tests are about.

Redis and Chroma are real services, never fakes: fakeredis's TCP server was
measured answering a blocking XREAD wrongly across processes, and the SSE path
is built on exactly that. Point the suite at them with

    QM_INTEGRATION_REDIS_URL=redis://[:password@]host:port/db
    QM_INTEGRATION_CHROMA_URL=http://host:port

(CI's backend job runs both as service containers; locally `make up` publishes
Redis on 6379 and Chroma on 8001). Without them the module is skipped and says
why. Each stack gets its own STATE_KEY_PREFIX and CHROMA_COLLECTION, so runs
share a Redis and a Chroma server without seeing each other, and every file is
under tmp_path.

The processes run with `PYTEST_CURRENT_TEST` removed from their environment:
the application skips its startup tasks when it sees that variable, and a
worker that skipped them is not the worker being tested.
"""

from __future__ import annotations

import base64
import os
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ADMIN_USERNAME = "stackadmin"
ADMIN_PASSWORD = "Stack-admin-password-10!"
_STARTUP_SECONDS = 90.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _tail(path: Path, lines: int = 60) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return "(no log)"


def _services() -> tuple[str, str]:
    redis_url = os.environ.get("QM_INTEGRATION_REDIS_URL", "").strip()
    chroma_url = os.environ.get("QM_INTEGRATION_CHROMA_URL", "").strip()
    if not redis_url or not chroma_url:
        pytest.skip("set QM_INTEGRATION_REDIS_URL and QM_INTEGRATION_CHROMA_URL to run the multi-process suite")
    _wait_for_services(redis_url, chroma_url)
    return redis_url, chroma_url


def _wait_for_services(redis_url: str, chroma_url: str, timeout: float = 60.0) -> None:
    """Both must answer before anything starts: a CI service container can be up before its server is.

    Configured and unreachable is a failure, not a skip -- somebody asked for
    this suite to run.
    """

    import redis

    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            redis.Redis.from_url(redis_url, socket_connect_timeout=2).ping()
            if httpx.get(f"{chroma_url.rstrip('/')}/api/v2/heartbeat", timeout=2).status_code == 200:
                return
            last = "chroma heartbeat not 200"
        except Exception as exc:  # noqa: BLE001 -- retried until the deadline, then reported
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(1)
    raise RuntimeError(f"Redis/Chroma not reachable after {timeout}s: {last}")


@dataclass
class Process:
    name: str
    command: list[str]
    log: Path
    handle: subprocess.Popen | None = None
    base_url: str = ""

    @property
    def pid(self) -> int:
        assert self.handle is not None
        return self.handle.pid

    def alive(self) -> bool:
        return self.handle is not None and self.handle.poll() is None


@dataclass
class Stack:
    root: Path
    env: dict[str, str]
    redis_url: str
    chroma_url: str
    prefix: str
    collection: str
    workers: list[Process] = field(default_factory=list)
    ingest: Process | None = None
    _logs: list = field(default_factory=list)

    # ---- processes ------------------------------------------------------------

    def start(self, process: Process) -> Process:
        log = open(process.log, "a", encoding="utf-8")  # noqa: SIM115 -- closed in stop()
        self._logs.append(log)
        process.handle = subprocess.Popen(
            process.command, env=self.env, cwd=self.root, stdout=log, stderr=subprocess.STDOUT
        )
        return process

    def kill(self, process: Process) -> None:
        """No shutdown handler runs: SIGKILL on POSIX, TerminateProcess on Windows."""

        if process.alive():
            process.handle.kill()
            process.handle.wait(timeout=10)

    def stop(self, process: Process) -> None:
        if process.alive():
            process.handle.terminate()
            try:
                process.handle.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.kill(process)

    def wait_healthy(self, process: Process, timeout: float = _STARTUP_SECONDS) -> None:
        deadline = time.monotonic() + timeout
        with httpx.Client(timeout=3.0) as client:
            while time.monotonic() < deadline:
                if not process.alive():
                    raise RuntimeError(f"{process.name} exited with {process.handle.returncode}:\n{_tail(process.log)}")
                try:
                    if client.get(f"{process.base_url}/health").status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.3)
        raise TimeoutError(f"{process.name} not healthy after {timeout}s:\n{_tail(process.log)}")

    def api_worker(self, name: str) -> Process:
        port = _free_port()
        command = [sys.executable, "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", str(port)]
        command += ["--log-level", "warning"]
        process = Process(name, command, self.root / f"{name}.log", base_url=f"http://127.0.0.1:{port}")
        return process

    def restart(self, process: Process) -> None:
        self.stop(process)
        fresh = self.api_worker(process.name)
        process.command, process.base_url = fresh.command, fresh.base_url
        self.start(process)
        self.wait_healthy(process)

    # ---- clients ----------------------------------------------------------------

    def login(self, worker: Process, username: str = ADMIN_USERNAME, password: str = ADMIN_PASSWORD) -> httpx.Client:
        response = httpx.post(f"{worker.base_url}/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return self.client(worker, response.json()["token"])

    def client(self, worker: Process, token: str) -> httpx.Client:
        # A new connection per request: uvicorn closes an idle keep-alive after
        # 5s, and a client that slept through a Retry-After of about that long
        # reused the socket the server had just closed (WinError 10053).
        return httpx.Client(
            base_url=worker.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120.0,
            limits=httpx.Limits(max_keepalive_connections=0),
        )

    def redis(self):
        import redis

        return redis.Redis.from_url(self.redis_url, decode_responses=True)

    def key(self, *parts: str) -> str:
        return self.prefix + ":".join(parts)


def _environment(root: Path, redis_url: str, chroma_url: str, prefix: str, collection: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "PYTEST_CURRENT_TEST"}
    empty = root / "empty.runtime.env"
    empty.write_text("", encoding="utf-8")
    env.update(
        {
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONUNBUFFERED": "1",
            "RUNTIME_ENV_FILE": str(empty),
            "APP_ENV": "test",
            "NACOS_ENABLED": "false",
            "MODEL_BACKEND": "local",
            "API_SETTINGS_ENCRYPTION_KEY": base64.urlsafe_b64encode(b"0" * 32).decode(),
            "ADMIN_USERNAME": ADMIN_USERNAME,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
            "AUTH_EXPOSE_TOKEN_IN_RESPONSE": "true",
            "AUTH_COOKIE_SECURE": "false",
            "CORS_ALLOW_ORIGINS": "*",
            "AUTO_INGEST_ENABLED": "false",
            # Each process is one worker; it is the processes that are several.
            "APP_WORKERS": "1",
            "STATE_BACKEND": "shared",
            "STATE_KEY_PREFIX": prefix,
            "HISTORY_BACKEND": "sqlite",
            "SESSION_METADATA_BACKEND": "database",
            "REDIS_URL": redis_url,
            "CHROMA_SERVER_URL": chroma_url,
            "CHROMA_COLLECTION": collection,
            "RETRIEVAL_CACHE_BACKEND": "redis",
            "QUERY_GUARD_BACKEND": "redis",
            # What these scenarios are not about, switched off so a query costs
            # well under a second and never leaves the machine: web search on an
            # empty corpus reached the live internet (measured: an answer about
            # Kafka to a question about backups), and the reranker, the NLI
            # stage and a local embedding model each load weights a CI runner
            # does not have. An absent embedding model falls back to hash
            # embeddings, which is what CI runs anyway.
            "WEB_SEARCH_ON_EMPTY_CORPUS": "false",
            "ENABLE_RERANKER": "false",
            "CASCADE_ENABLE_NLI": "false",
            "CASCADE_ENABLE_DEEP": "false",
            "LOCAL_EMBED_MODEL": "qm-integration/absent-model",
            "APP_DB_PATH": str(root / "data" / "app.db"),
            "DATABASE_URL": f"sqlite:///{(root / 'data' / 'querymind.db').as_posix()}",
        }
    )
    return env


def _run_init(env: dict[str, str], root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.init_app"], env=env, cwd=root, capture_output=True, text=True, timeout=180
    )
    assert result.returncode == 0, (
        f"init failed ({result.returncode}):\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
    )


def _drop_redis_keys(stack: Stack) -> None:
    try:
        client = stack.redis()
        keys = list(client.scan_iter(match=f"{stack.prefix}*", count=1000))
        if keys:
            client.delete(*keys)
    except Exception:  # noqa: BLE001 -- teardown of a scratch namespace
        pass


def _drop_collection(stack: Stack) -> None:
    try:
        from app.retrievers.stores.vector import chroma_http_client

        client = chroma_http_client(stack.chroma_url)
    except Exception:  # noqa: BLE001 -- teardown of a scratch collection
        return
    # MODEL_BACKEND=local names its collection `<CHROMA_COLLECTION>_local`.
    for name in (stack.collection, f"{stack.collection}_local"):
        try:
            client.delete_collection(name)
        except Exception:  # noqa: BLE001, S112 -- the collection may never have been created
            continue


def build_stack(root: Path, **overrides: str) -> Generator[Stack, None, None]:
    """Start init, the ingest worker and two API workers; yield; stop and clean up."""

    redis_url, chroma_url = _services()
    run = uuid.uuid4().hex[:8]
    prefix, collection = f"qmt{run}:", f"qmt_{run}"
    env = _environment(root, redis_url, chroma_url, prefix, collection)
    env.update(overrides)
    stack = Stack(root=root, env=env, redis_url=redis_url, chroma_url=chroma_url, prefix=prefix, collection=collection)
    try:
        _run_init(env, root)
        stack.ingest = stack.start(
            Process("ingest-worker", [sys.executable, "-m", "app.ingest_worker"], root / "ingest-worker.log")
        )
        stack.workers = [stack.start(stack.api_worker("worker-a")), stack.start(stack.api_worker("worker-b"))]
        for worker in stack.workers:
            stack.wait_healthy(worker)
        yield stack
    finally:
        for process in [*stack.workers, *([stack.ingest] if stack.ingest else [])]:
            stack.stop(process)
        for log in stack._logs:
            log.close()
        _drop_redis_keys(stack)
        _drop_collection(stack)
