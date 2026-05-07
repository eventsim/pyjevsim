"""Transport contract + LoopbackTransport + _HLARouter.

Spec: docs/hla/specification.md §2.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

OnReceive = Callable[[str, str, Any, "float | None"], None]


class Transport(Protocol):
    def send(self, binding, payload: Any) -> None: ...
    def on_receive(self, callback: OnReceive) -> None: ...
    def request_time_advance(self, target: float) -> float: ...
    def close(self) -> None: ...


class LoopbackTransport:
    """In-process transport: mirrors out→in to a single registered callback.

    Test-only. send on direction="in" is a no-op (loopback only mirrors
    out→in). request_time_advance is identity. close is idempotent.
    """

    def __init__(self) -> None:
        self._cb: OnReceive | None = None

    def send(self, binding, payload: Any) -> None:
        # §2.2: only mirror out and inout (the outbound side).
        if binding.direction not in ("out", "inout"):
            return
        if self._cb is None:
            return
        self._cb(binding.kind, binding.fom_id, payload, None)

    def on_receive(self, callback: OnReceive) -> None:
        self._cb = callback

    def request_time_advance(self, target: float) -> float:
        return target

    def close(self) -> None:
        self._cb = None


class _HLARouter:
    """Single subscriber on a Transport; demultiplexes to HLAExecutors.

    Spec §2.3. One per transport. Multiple executors may subscribe to
    the same (kind, fom_id); all receive each event.
    """

    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self._subs: dict[tuple[str, str], list] = {}
        transport.on_receive(self._dispatch)

    def subscribe(self, kind: str, fom_id: str, executor) -> None:
        self._subs.setdefault((kind, fom_id), []).append(executor)

    def unsubscribe(self, kind: str, fom_id: str, executor) -> None:
        key = (kind, fom_id)
        lst = self._subs.get(key)
        if not lst:
            return
        try:
            lst.remove(executor)
        except ValueError:
            return
        if not lst:
            del self._subs[key]

    def _dispatch(self, kind: str, fom_id: str, payload: Any,
                  timestamp: float | None) -> None:
        for ex in tuple(self._subs.get((kind, fom_id), ())):
            ex._on_rti_event(kind, fom_id, payload, timestamp)
