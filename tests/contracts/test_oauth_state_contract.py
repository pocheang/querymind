"""OAuth state behaves the same in Redis and in process memory (ARC-01 phase 10).

The state is the CSRF defence of the Google sign-in: created when the redirect
leaves, consumed exactly once when the callback returns. With STATE_BACKEND=shared
it lives in Redis, because the callback may land on another worker; otherwise
in Redis when it answers and in memory when it does not. Whichever holds it,
a state is single-use, bound to the address that asked for it, and gone after
its TTL.

The memory variant is pinned off Redis by a permanent cooldown rather than by
passing no URL: the store falls back to redis://localhost:6379, and `make up`
publishes a Redis exactly there.
"""

from __future__ import annotations

import time

import pytest

from app.services.auth.oauth_state import OAuthStateStore

IP = "198.51.100.7"


@pytest.fixture(params=["memory", "redis"])
def store(request, sync_redis, install, monkeypatch) -> OAuthStateStore:
    built = OAuthStateStore("redis://contract-test:6379/0")
    if request.param == "memory":
        monkeypatch.setattr(built._redis, "_client", None)
        monkeypatch.setattr(built._redis, "_unavailable_until", float("inf"))
    else:
        install(built._redis, sync_redis)
    return built


def test_a_created_state_carries_its_data(store):
    state = store.create({"ip": IP, "next": "/chat"})

    assert store.get(state) == {"ip": IP, "next": "/chat"}


def test_states_are_distinct_and_url_safe(store):
    states = {store.create({"ip": IP}) for _ in range(20)}

    assert len(states) == 20
    assert all(state.replace("-", "").replace("_", "").isalnum() for state in states)


def test_a_state_is_consumed_exactly_once(store):
    state = store.create({"ip": IP})

    assert store.consume(state, IP) == (None, IP)
    assert store.consume(state, IP) == ("invalid_state", None)


def test_a_state_returned_from_another_address_is_refused_and_spent(store):
    """A replay from the right address must not succeed after the wrong one tried."""

    state = store.create({"ip": IP})

    assert store.consume(state, "203.0.113.9") == ("security_check_failed", IP)
    assert store.consume(state, IP) == ("invalid_state", None)


@pytest.mark.parametrize("state", [None, "", "never-created"])
def test_a_missing_or_unknown_state_is_invalid(store, state):
    assert store.consume(state, IP) == ("invalid_state", None)


def test_a_deleted_state_is_gone(store):
    state = store.create({"ip": IP})

    store.delete(state)

    assert store.get(state) is None
    assert store.consume(state, IP) == ("invalid_state", None)


def test_a_state_expires_after_its_ttl(store):
    state = store.create({"ip": IP}, ttl_seconds=1)
    assert store.get(state) is not None

    time.sleep(1.2)

    assert store.get(state) is None
    assert store.consume(state, IP) == ("invalid_state", None)
