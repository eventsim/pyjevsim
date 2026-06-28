"""InProcessRTI — a multi-federate, in-process stand-in for an RTI.

Unlike :class:`~pyjevsim.hla.transport.LoopbackTransport` (which mirrors a
single connector's output straight back to itself), ``InProcessRTI`` attaches
multiple connectors to a shared :class:`InProcessFederation` bus. A ``send``
from one connector is delivered to *every other* attached connector, exactly
like a real federation — so two separate ``SysExecutor`` federates (e.g. ping
and pong) can exchange interactions and object-attribute updates in one
process, with no Java/RTI required.

Subscription filtering is still done per-connector by the ``_HLARouter``, so
each federate only sees the ``(kind, fom_id)`` pairs it subscribed to.

Registered under the name ``"inprocess"``.
"""

from __future__ import annotations

from typing import Any

from ..registry import register_rti
from ..transport import RTICapabilities, RTIConnector


class InProcessFederation:
    """Shared bus standing in for a federation execution.

    Connectors attach on ``join`` and detach on ``resign``/``close``. The
    bus broadcasts each send to every *other* attached connector.
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._members: list = []

    @property
    def members(self) -> tuple:
        return tuple(self._members)

    def attach(self, conn) -> None:
        if conn not in self._members:
            self._members.append(conn)

    def detach(self, conn) -> None:
        if conn in self._members:
            self._members.remove(conn)

    def broadcast(self, sender, kind: str, fom_id: str, wire: Any,
                  timestamp: "float | None") -> None:
        # Snapshot so a callback that resigns mid-dispatch can't mutate the
        # list under iteration.
        for m in tuple(self._members):
            if m is not sender:
                m._emit(kind, fom_id, wire, timestamp)


class InProcessRTI(RTIConnector):
    """In-process connector attached to an :class:`InProcessFederation`."""

    capabilities = RTICapabilities(
        name="inprocess",
        time_management=True,
        timestamp_ordered=True,
        interactions=True,
        object_attributes=True,
    )

    def __init__(self, federation: "InProcessFederation | None" = None,
                 codec=None, **_ignored) -> None:
        super().__init__(codec)
        self._fed = federation if federation is not None else InProcessFederation()

    @property
    def federation(self) -> InProcessFederation:
        return self._fed

    # --- RTI-specific hooks -------------------------------------------------

    def _do_send(self, binding, wire: Any, timestamp: "float | None") -> None:
        self._fed.broadcast(self, binding.kind, binding.fom_id, wire, timestamp)

    def _do_request_time_advance(self, target: float) -> float:
        # No global time coordination in-process: identity grant. Callers
        # that need lock-step semantics drive each federate's `step()`
        # explicitly (see examples/hla_pingpong).
        return target

    def _do_join(self, federation: str, federate_name: str, fom_paths) -> None:
        self._fed.attach(self)

    def _do_resign(self) -> None:
        self._fed.detach(self)

    def _do_close(self) -> None:
        self._fed.detach(self)


register_rti("inprocess", lambda **kw: InProcessRTI(**kw))
