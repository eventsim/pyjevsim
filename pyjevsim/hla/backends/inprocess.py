"""In-process bus for examples and protocol-level tests.

Each ``InProcessRTI`` connector joins an ``InProcessFederation``. Values sent
by one connector are delivered to the other attached connectors, while each
connector's router applies subscription filtering. The bus does not provide
federation-wide HLA time management or network transport.
"""

from __future__ import annotations

from typing import Any

from ..registry import register_rti
from ..transport import RTICapabilities, RTIConnector


class InProcessFederation:
    """Bus shared by in-process connectors.

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
        # Copy the member list because a callback may resign during dispatch.
        for m in tuple(self._members):
            if m is not sender:
                m._emit(kind, fom_id, wire, timestamp)


class InProcessRTI(RTIConnector):
    """In-process connector attached to an :class:`InProcessFederation`."""

    capabilities = RTICapabilities(
        name="inprocess",
        # This test bus returns identity grants and forwards in caller order;
        # it does not implement federation-wide HLA time management or TSO.
        time_management=False,
        timestamp_ordered=False,
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

    def _do_send(self, binding, wire: Any, timestamp: "float | None") -> None:
        self._fed.broadcast(self, binding.kind, binding.fom_id, wire, timestamp)

    def _do_request_time_advance(self, target: float) -> float:
        # This bus has no global time coordination; callers coordinate steps.
        return target

    def _do_join(self, federation: str, federate_name: str, fom_paths) -> None:
        self._fed.attach(self)

    def _do_resign(self) -> None:
        self._fed.detach(self)

    def _do_close(self) -> None:
        self._fed.detach(self)


register_rti("inprocess", lambda **kw: InProcessRTI(**kw))
