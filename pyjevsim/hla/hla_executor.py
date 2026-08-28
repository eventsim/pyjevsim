"""Connect a ``BehaviorExecutor`` to an HLA transport.

Bound output ports send through the transport. Received events enter the
parent executor through generated input ports and couplings. See
``docs/hla/specification.md`` section 3.
"""

from __future__ import annotations

from typing import Any

from ..behavior_executor import BehaviorExecutor
from ..message_deliverer import MessageDeliverer


class HLAExecutor(BehaviorExecutor):
    def __init__(self, itime, dtime, ename, behavior_model, parent,
                 transport, bindings, router):
        super().__init__(itime, dtime, ename, behavior_model, parent)
        self._transport = transport
        self._bindings = dict(bindings)
        self._router = router

        # Check binding directions against the model's declared ports.
        in_ports = set(behavior_model.retrieve_input_ports())
        out_ports = set(behavior_model.retrieve_output_ports())
        for port, b in self._bindings.items():
            d = b.direction
            if d in ("in", "inout") and port not in in_ports:
                raise ValueError(
                    f"binding {b!r} references unknown input port {port!r} "
                    f"on model {behavior_model.get_name()!r}"
                )
            if d in ("out", "inout") and port not in out_ports:
                raise ValueError(
                    f"binding {b!r} references unknown output port {port!r} "
                    f"on model {behavior_model.get_name()!r}"
                )

        # coupling_relation resolves the destination through product_port_map.
        # Factory construction happens before register_entity fills this map,
        # so install the entry before creating inbound couplings.
        parent.product_port_map[behavior_model] = self

        self._inbound_routes: dict[tuple[str, str], tuple[str, str]] = {}
        for port, b in self._bindings.items():
            if b.direction not in ("in", "inout"):
                continue
            sys_port = f"_hla_{behavior_model.get_obj_id()}__{port}"
            if sys_port not in parent.retrieve_input_ports():
                parent.insert_input_port(sys_port)
            parent.coupling_relation(None, sys_port, behavior_model, port)
            self._inbound_routes[(b.kind, b.fom_id)] = (sys_port, port)
            router.subscribe(b.kind, b.fom_id, self)

    # -------------------------------------------------------- output

    def output(self, msg_deliver):
        inner = MessageDeliverer()
        self.behavior_model.output(inner)
        if not inner.has_contents():
            return
        for sys_msg in inner.get_contents():
            port = sys_msg.get_dst()
            b = self._bindings.get(port)
            if b is not None and b.direction in ("out", "inout"):
                self._transport.send(b, sys_msg.retrieve())
                continue
            msg_deliver.insert_message(sys_msg)

    # -------------------------------------------------------- inbound

    def _on_rti_event(self, kind: str, fom_id: str, payload: Any,
                      timestamp: float | None) -> None:
        route = self._inbound_routes.get((kind, fom_id))
        if route is None:
            return
        sys_port, _model_port = route
        now = self.parent.global_time
        ts = timestamp if timestamp is not None else now
        delay = max(0.0, ts - now)
        # insert_external_event wraps one value in a SysMessage. Insert each
        # payload item separately to preserve the sender's message shape.
        if not payload:
            return
        for item in payload:
            self.parent.insert_external_event(sys_port, item, scheduled_time=delay)
