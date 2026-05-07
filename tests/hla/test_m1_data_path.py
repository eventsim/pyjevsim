"""M1 — HLAExecutor data path: output interception + inbound injection.

Spec section: docs/hla/specification.md §3.
Acceptance IDs: M1.1 .. M1.11.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pyjevsim.hla.hla_executor")

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.behavior_executor import BehaviorExecutor
from pyjevsim.hla.bindings import HLAInteraction
from pyjevsim.hla.hla_executor import HLAExecutor
from pyjevsim.hla.transport import LoopbackTransport, _HLARouter
from pyjevsim.message_deliverer import MessageDeliverer

from .conftest import EmitOnce, RecordingReceiver


# ------------------------------------------------------------ helpers


def _new_sys_exec():
    return SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)


def _wrap(model, bindings, transport=None, sys_exec=None, router=None):
    """Construct an HLAExecutor with the router pattern from §2.3 / §3.1.

    Returns (executor, sys_exec, transport, router).
    """
    sys_exec = sys_exec or _new_sys_exec()
    transport = transport if transport is not None else LoopbackTransport()
    router = router if router is not None else _HLARouter(transport)
    ex = HLAExecutor(
        itime=0,
        dtime=float("inf"),
        ename="test",
        behavior_model=model,
        parent=sys_exec,
        transport=transport,
        bindings=bindings,
        router=router,
    )
    return ex, sys_exec, transport, router


# ------------------------------------------------------------ class shape


class TestClassShape:
    def test_M1_1_is_subclass_of_behavior_executor(self):
        assert issubclass(HLAExecutor, BehaviorExecutor), (
            "§3.1: HLAExecutor inherits from BehaviorExecutor"
        )

    def test_M1_2_constructor_stores_bindings_and_parent(self, emitter):
        # §3.1 — observable behavior, not private attrs: a bound out
        # port emits via the transport.
        bindings = {
            "out": HLAInteraction("Communication.ChatMsg", direction="out"),
        }
        tx = LoopbackTransport()
        seen: list = []
        tx.on_receive(lambda kind, fom_id, payload, ts:
                      seen.append((kind, fom_id, payload)))

        ex, sys_exec, _, _ = _wrap(emitter, bindings, transport=tx)
        ex.output(MessageDeliverer())

        assert seen == [("interaction", "Communication.ChatMsg",
                         [{"hello": "world"}])]
        # parent is the SysExecutor passed at construction time.
        assert ex.parent is sys_exec

    def test_M1_3_unknown_port_raises(self, emitter):
        bindings = {"not_a_port": HLAInteraction("X", direction="out")}
        with pytest.raises(ValueError):
            _wrap(emitter, bindings)


# ------------------------------------------------------------ output path


class TestOutputInterception:
    def test_M1_4_bound_out_port_goes_to_transport(self, emitter):
        bindings = {"out": HLAInteraction("Comm.Chat", direction="out")}
        sent: list = []
        tx = LoopbackTransport()
        # Patch send so we observe the call without delivery side-effects.
        original_send = tx.send
        def spy(b, payload):
            sent.append((b, payload))
            original_send(b, payload)
        tx.send = spy  # type: ignore[assignment]

        ex, _, _, _ = _wrap(emitter, bindings, transport=tx)
        deliver = MessageDeliverer()
        ex.output(deliver)

        assert len(sent) == 1, "§3.2: bound out-port must reach transport.send"
        binding, payload = sent[0]
        assert binding.fom_id == "Comm.Chat"
        assert payload == [{"hello": "world"}], (
            "send receives sys_msg.retrieve() (a list of inserted items)"
        )
        assert not deliver.has_contents(), (
            "§3.2: bound out-port must NOT also reach the outer msg_deliver"
        )

    def test_M1_5_unbound_port_flows_through_msg_deliver(self):
        emitter = EmitOnce(name="e", out_port="local")
        ex, _, tx, _ = _wrap(emitter, bindings={})
        deliver = MessageDeliverer()
        ex.output(deliver)
        assert deliver.has_contents(), (
            "§3.2: unbound port must flow through msg_deliver normally"
        )

    def test_M1_6_inout_binding_routes_outbound_to_transport(self):
        emitter = EmitOnce(name="e", out_port="dual")
        bindings = {"dual": HLAInteraction("Comm.X", direction="inout")}
        sent: list = []
        tx = LoopbackTransport()
        tx.send = lambda b, p: sent.append((b, p))  # type: ignore[assignment]

        ex, _, _, _ = _wrap(emitter, bindings, transport=tx)
        deliver = MessageDeliverer()
        ex.output(deliver)
        assert len(sent) == 1, (
            "§3.2: inout binding must route outbound to transport"
        )

    def test_M1_10_empty_bindings_behaves_like_behavior_executor(self):
        emitter = EmitOnce(name="e", out_port="local")
        sent: list = []
        tx = LoopbackTransport()
        tx.send = lambda *a, **k: sent.append(a)  # type: ignore[assignment]

        ex, _, _, _ = _wrap(emitter, bindings={}, transport=tx)
        deliver = MessageDeliverer()
        ex.output(deliver)
        assert sent == [], (
            "§3.5: empty bindings must produce zero transport calls"
        )
        assert deliver.has_contents()

    def test_M1_11_send_exception_propagates(self, emitter):
        bindings = {"out": HLAInteraction("X", direction="out")}
        tx = LoopbackTransport()

        def boom(*a, **k):
            raise RuntimeError("transport down")
        tx.send = boom  # type: ignore[assignment]

        ex, _, _, _ = _wrap(emitter, bindings, transport=tx)
        with pytest.raises(RuntimeError, match="transport down"):
            ex.output(MessageDeliverer())


# ------------------------------------------------------------ inbound path


class TestInboundInjection:
    """Inbound delivery via the §3.3 wiring (namespaced SE port + coupling).

    The constructor must register the SE-side port and add a coupling so
    `insert_external_event` actually queues the event. M1.7 verifies the
    end-to-end queueing; M1.8 verifies non-subscribed events are dropped
    silently; M1.9 verifies the past-timestamp clamp.
    """

    def test_M1_7_subscribed_event_is_queued_on_namespaced_port(self):
        receiver = RecordingReceiver(name="r", in_port="inbox")
        bindings = {"inbox": HLAInteraction("Comm.Chat", direction="in")}

        ex, sys_exec, _tx, _router = _wrap(receiver, bindings)

        # Namespaced SE-side port name per §3.3 step 1.
        sys_port = f"_hla_{receiver.get_obj_id()}__inbox"
        assert sys_port in sys_exec.retrieve_input_ports(), (
            "§3.3 step 2: constructor must insert namespaced port on parent"
        )

        # Inbound delivery as the router would invoke it.
        ex._on_rti_event("interaction", "Comm.Chat", [{"text": "yo"}], timestamp=0.0)

        assert len(sys_exec.input_event_queue) == 1, (
            "§3.4: subscribed event must result in insert_external_event"
        )
        _ts, sys_msg = sys_exec.input_event_queue[0]
        assert sys_msg.get_dst() == sys_port, (
            "queued event targets the namespaced SE port; coupling routes "
            "it to the model's input port"
        )

    def test_M1_8_unsubscribed_event_is_dropped(self):
        receiver = RecordingReceiver(name="r", in_port="inbox")
        bindings = {"inbox": HLAInteraction("Comm.Chat", direction="in")}

        ex, sys_exec, _tx, _router = _wrap(receiver, bindings)

        ex._on_rti_event("interaction", "OtherClass.X", [{"a": 1}], timestamp=0.0)
        assert sys_exec.input_event_queue == [], (
            "§3.4: events not in _inbound_routes must be dropped"
        )

    def test_M1_9_past_timestamp_clamps_delay_to_zero(self):
        receiver = RecordingReceiver(name="r", in_port="inbox")
        bindings = {"inbox": HLAInteraction("Comm.Chat", direction="in")}

        ex, sys_exec, _tx, _router = _wrap(receiver, bindings)
        sys_exec.global_time = 5.0

        ex._on_rti_event("interaction", "Comm.Chat", [{"x": 1}], timestamp=2.0)

        assert len(sys_exec.input_event_queue) == 1
        scheduled_t, _ = sys_exec.input_event_queue[0]
        # insert_external_event adds (scheduled_time + global_time). With
        # delay clamped to 0 and global_time=5.0, queue ts == 5.0.
        assert scheduled_t == 5.0, (
            "§3.4: past timestamp must clamp delay to 0; queued at global_time"
        )
