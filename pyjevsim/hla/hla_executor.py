"""HLAExecutor — decorates BehaviorExecutor with RTI bridging.

Spec: docs/hla/specification.md §3.

The wrapped BehaviorModel stays pure DEVS. HLAExecutor:
- intercepts output() messages on bound out/inout ports and ships them
  to the transport;
- registers namespaced SE-side ports + couplings so inbound RTI events
  delivered via parent.insert_external_event reach the model;
- subscribes with the shared _HLARouter so the transport's single
  callback fans out correctly to multiple executors.
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

        # Validate every binding's port name against the model.
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

        # §3.3 construction-time wiring: namespaced SE port + coupling
        # + router subscription, for each in/inout binding.
        #
        # `coupling_relation` looks dst_obj up in `product_port_map`,
        # which `register_entity` populates AFTER `create_executor`
        # returns. Pre-populate it here so wiring works whether the
        # executor was built via the factory or directly in a test.
        # `register_entity` will overwrite the entry with the same
        # value moments later — harmless.
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
        # Payload is the list returned by SysMessage.retrieve() on the
        # sending side (§2.1). insert_external_event wraps its `_msg`
        # arg as a single SysMessage item, so we inject one item at a
        # time to preserve the original message shape on the receiver.
        if not payload:
            return
        for item in payload:
            self.parent.insert_external_event(sys_port, item, scheduled_time=delay)
