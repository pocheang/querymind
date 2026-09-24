"""Pytest fixtures for multi-worker integration testing.

Spawns two real, independent uvicorn processes on distinct ports to test
behavior across worker boundaries (ARC-01 Phase 0).
"""

import base64
import os
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from pathlib import Path

import httpx
import pytest


def _find_free_port() -> int:
    """Find an available port assigned by the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _terminate_process(proc: subprocess.Popen, log_file) -> None:
    """Gracefully terminate a subprocess, falling back to kill if it hangs."""
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    except Exception:
        pass
    finally:
        try:
            log_file.close()
        except Exception:
            pass


def _tail_lines(text: str, n: int = 80) -> str:
    """Return the last n lines of text."""
    lines = text.splitlines()
    return "\n".join(lines[-n:])


@pytest.fixture(scope="module")
def two_workers(tmp_path_factory) -> Generator[dict, None, None]:
    """Start two independent uvicorn worker processes and yield their connection info."""
    temp_dir = tmp_path_factory.mktemp("multiworker")
    repo_root = Path(__file__).resolve().parents[3]

    port1 = _find_free_port()
    port2 = _find_free_port()
    while port2 == port1:
        port2 = _find_free_port()

    runtime_env_file = temp_dir / "empty.runtime.env"
    runtime_env_file.write_text("", encoding="utf-8")

    # Configure isolated environment for both worker processes
    env = os.environ.copy()
    env["APP_WORKERS"] = "1"
    env["API_SETTINGS_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"0" * 32).decode()
    env["APP_ENV"] = "test"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(repo_root)
    env["RUNTIME_ENV_FILE"] = str(runtime_env_file)
    env["APP_DB_PATH"] = str(temp_dir / "app.db")
    env["CHROMA_PERSIST_DIR"] = str(temp_dir / "chroma")
    env["MODEL_BACKEND"] = "local"
    env["NACOS_ENABLED"] = "false"
    env["AUTO_INGEST_ENABLED"] = "false"
    env["AUTH_REGISTER_MAX_ATTEMPTS"] = "3"
    env["REDIS_URL"] = "redis://127.0.0.1:1/0"
    env["RETRIEVAL_CACHE_BACKEND"] = "memory"
    env["CORS_ALLOW_ORIGINS"] = "*"

    log_path1 = temp_dir / "worker_1.log"
    log_path2 = temp_dir / "worker_2.log"
    log1 = open(log_path1, "w+", encoding="utf-8")
    log2 = open(log_path2, "w+", encoding="utf-8")

    cmd1 = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port1),
        "--workers",
        "1",
        "--log-level",
        "warning",
    ]
    cmd2 = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port2),
        "--workers",
        "1",
        "--log-level",
        "warning",
    ]

    proc1 = subprocess.Popen(cmd1, env=env, cwd=temp_dir, stdout=log1, stderr=subprocess.STDOUT)
    # Staggered on purpose, and only until ARC-01 phase 7: two workers started together
    # can crash with 'database is locked' while the other creates the schema. That defect
    # is pinned deterministically, as a strict xfail, in
    # tests/services/test_auth_store_waits_for_a_concurrent_writer.py -- this fixture is
    # for everything else two workers disagree about, and must not flake on it.
    time.sleep(1.0)
    proc2 = subprocess.Popen(cmd2, env=env, cwd=temp_dir, stdout=log2, stderr=subprocess.STDOUT)

    worker_info = {
        "worker_1": {"base_url": f"http://127.0.0.1:{port1}", "pid": proc1.pid},
        "worker_2": {"base_url": f"http://127.0.0.1:{port2}", "pid": proc2.pid},
    }

    # Poll /health on both workers until ready
    max_wait_seconds = 45.0
    start_time = time.time()
    worker1_ready = False
    worker2_ready = False

    try:
        with httpx.Client(timeout=2.0) as client:
            while time.time() - start_time < max_wait_seconds:
                # Check worker 1
                if not worker1_ready:
                    if proc1.poll() is not None:
                        log1.seek(0)
                        output = _tail_lines(log1.read(), 80)
                        raise RuntimeError(f"Worker 1 exited prematurely with code {proc1.returncode}:\n{output}")
                    try:
                        r1 = client.get(f"{worker_info['worker_1']['base_url']}/health")
                        if r1.status_code == 200:
                            worker1_ready = True
                    except (httpx.ConnectError, httpx.TimeoutException):
                        pass

                # Check worker 2
                if not worker2_ready:
                    if proc2.poll() is not None:
                        log2.seek(0)
                        output = _tail_lines(log2.read(), 80)
                        raise RuntimeError(f"Worker 2 exited prematurely with code {proc2.returncode}:\n{output}")
                    try:
                        r2 = client.get(f"{worker_info['worker_2']['base_url']}/health")
                        if r2.status_code == 200:
                            worker2_ready = True
                    except (httpx.ConnectError, httpx.TimeoutException):
                        pass

                if worker1_ready and worker2_ready:
                    break

                time.sleep(0.3)

        if not (worker1_ready and worker2_ready):
            log1.seek(0)
            log2.seek(0)
            log1_tail = _tail_lines(log1.read(), 80)
            log2_tail = _tail_lines(log2.read(), 80)
            raise TimeoutError(
                f"Timed out after {max_wait_seconds}s waiting for workers to be healthy.\n"
                f"Worker 1 (ready={worker1_ready}) log (last 80 lines):\n{log1_tail}\n"
                f"Worker 2 (ready={worker2_ready}) log (last 80 lines):\n{log2_tail}"
            )

        yield worker_info

    finally:
        _terminate_process(proc1, log1)
        _terminate_process(proc2, log2)
