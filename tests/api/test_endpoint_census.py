"""The OpenAPI document must still publish the operations it published yesterday.

A refactor that drops a router does not fail anything. The application starts,
every test that does not touch those paths passes, and the endpoints are simply
gone -- which is why this count is asserted at all.

It was asserted in the CI workflow as an inline ``python -c`` with a floor of
``n >= 140`` against an actual 157. Seventeen operations -- a whole router, and
then some -- could disappear with the step still green, which is the shape this
repository keeps recording: a check whose threshold is far enough from reality
that it cannot fail for the reason it exists. The baseline is exact here, so a
change to it is a line in a diff somebody can ask about.

Adding endpoints therefore fails too, and deliberately: ``EXPECTED_OPERATIONS``
is the only place the number is stated, and a count nothing recomputes goes
stale exactly the way the one in CLAUDE.md did (153 for weeks after it was 157).
The failure message says which way it moved and what to do about it.

Counting OpenAPI operations rather than ``len(app.routes)`` is load-bearing:
FastAPI 0.138+ stores an ``_IncludedRouter`` wrapper in ``app.routes`` instead of
flattening child routes, so that number varies by FastAPI version (30 on 0.138.2
against 156 on 0.135.3) and would make this test a version check.
"""

from __future__ import annotations

import pytest

_METHODS = frozenset({"get", "post", "put", "patch", "delete"})

# Update in the same commit that changes the surface, and say why in the message.
EXPECTED_OPERATIONS = 157


def _operations() -> dict[str, list[str]]:
    main = pytest.importorskip("app.api.main")
    paths = main.app.openapi()["paths"]
    return {path: sorted(m for m in item if m in _METHODS) for path, item in paths.items()}


def test_the_census_counts_something() -> None:
    """A zero here would make the assertion below pass for the wrong reason."""

    assert _operations()


def test_the_published_operation_count_is_the_baseline() -> None:
    operations = _operations()
    total = sum(len(methods) for methods in operations.values())

    if total < EXPECTED_OPERATIONS:
        pytest.fail(
            f"the OpenAPI document publishes {total} operations, down from {EXPECTED_OPERATIONS}. "
            f"A dropped router is the usual cause -- check that every router is still included in "
            f"app/api/main.py. If the removal is deliberate, lower EXPECTED_OPERATIONS here."
        )
    assert total == EXPECTED_OPERATIONS, (
        f"the OpenAPI document publishes {total} operations, up from {EXPECTED_OPERATIONS}. "
        f"Raise EXPECTED_OPERATIONS to {total} in the same commit that adds them, so the new "
        f"surface is what the next change has to keep."
    )
