"""The default multi-process stack for this directory; see multiworker_stack.py."""

from __future__ import annotations

import pytest
from multiworker_stack import Stack, build_stack


@pytest.fixture(scope="module")
def stack(tmp_path_factory) -> Stack:
    yield from build_stack(tmp_path_factory.mktemp("stack"))
