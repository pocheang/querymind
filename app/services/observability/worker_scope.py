"""Which process answered: attached to every admin view built from one worker's memory (ARC-01 phase 8).

Some of what the admin console shows is kept per process and is correct that
way -- the recent-request window behind the runtime panel and the overview's
latency figures, the captured log buffer, the circuit breakers. With several
workers each of those is one worker's slice, and which one depends on where the
request landed. Saying so is the fix: a figure labelled with the pid that
produced it can be read correctly, and one that is not reads as the whole
deployment.
"""

from __future__ import annotations

import os
import socket


def this_worker() -> dict[str, object]:
    """The pid and host of the process answering, for a response built from its own memory."""

    return {"pid": os.getpid(), "host": socket.gethostname()}
