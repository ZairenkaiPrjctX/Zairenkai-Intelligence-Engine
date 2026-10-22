# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""In-process network guard: any socket connection or name lookup during the agent loop fails and
is recorded. The model process itself runs in an empty network namespace (runtime.py); this guard
covers the Python side, so a test can prove the whole loop made no network attempt."""
from __future__ import annotations

import socket
from contextlib import contextmanager
from typing import Iterator


class NetworkBlocked(OSError):
    pass


@contextmanager
def no_network(attempts: list[str]) -> Iterator[list[str]]:
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo)

    def refuse(what: str):
        def blocked(*args, **kwargs):
            target = args[1] if len(args) > 1 else args[0] if args else "?"
            attempts.append(f"{what} {target!r}")
            raise NetworkBlocked(f"network access blocked in the local agent: {what}")
        return blocked

    socket.socket.connect = refuse("connect")  # type: ignore[method-assign]
    socket.socket.connect_ex = refuse("connect_ex")  # type: ignore[method-assign]
    socket.create_connection = refuse("create_connection")  # type: ignore[assignment]
    socket.getaddrinfo = refuse("getaddrinfo")  # type: ignore[assignment]
    try:
        yield attempts
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection, socket.getaddrinfo = saved  # type: ignore[method-assign]
