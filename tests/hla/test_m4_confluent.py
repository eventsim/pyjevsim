"""M4 — Confluent / bag-delivery semantics for inbound RTI events.

Spec section: docs/hla/specification.md §6.
Acceptance IDs: M4.1 .. M4.5.

These tests exercise the interaction between transport-injected events
and SysExecutor.step rounds. The implementation work for M4 is
*usually* zero new code — the tests verify that the existing step loop
does the right thing once HLAExecutor is in place. A failing test here
is a real bug, not a missing feature.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pyjevsim.hla.federate")

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla.bindings import HLAInteraction
from pyjevsim.hla.factory import HLAExecutorFactory
from pyjevsim.hla.transport import LoopbackTransport

from .conftest import ConfluentCounter, RecordingReceiver


def _sys():
    return SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)


def _build_one_receiver(model_name="counter", in_port="in"):
    """Returns (sys_exec, transport, model) wired with one bound input port."""
    tx = LoopbackTransport()
    sys_exec = _sys()
    sys_exec.exec_factory = HLAExecutorFactory(
        tx,
        bindings_by_model={
            model_name: {in_port: HLAInteraction("Comm.X", direction="in")},
        },
    )
    return sys_exec, tx


class TestConfluentDelivery:
    def test_M4_1_imminent_plus_inbound_triggers_con_trans_once(self):
        sys_exec, tx = _build_one_receiver()
        counter = ConfluentCounter(name="counter", deadline=0.0)
        sys_exec.register_entity(counter)

        # Find the HLAExecutor for the counter and inject an event at t=0.
        ex = sys_exec.model_map["counter"][0]
        ex._on_rti_event("interaction", "Comm.X", [{"v": 1}], timestamp=0.0)

        sys_exec.step(0.0)

        assert counter.n_con == 1, (
            "§6: imminent + inbound at the same instant must produce one con_trans"
        )
        assert counter.n_int == 0
        assert counter.n_ext == 0

    def test_M4_2_non_imminent_plus_inbound_triggers_ext_trans(self):
        sys_exec, tx = _build_one_receiver()
        # Deadline of 5 — not imminent at t=0.
        counter = ConfluentCounter(name="counter", deadline=5.0)
        sys_exec.register_entity(counter)

        ex = sys_exec.model_map["counter"][0]
        ex._on_rti_event("interaction", "Comm.X", [{"v": 1}], timestamp=0.0)
        sys_exec.step(0.0)

        assert counter.n_ext == 1
        assert counter.n_con == 0
        assert counter.n_int == 0

    def test_M4_3_two_inbound_events_same_instant_delivered_together(self):
        # Two ports on the same model, both inbound, same timestamp.
        tx = LoopbackTransport()
        sys_exec = _sys()
        bindings = {
            "rcv": {
                "in_a": HLAInteraction("A", direction="in"),
                "in_b": HLAInteraction("B", direction="in"),
            }
        }
        sys_exec.exec_factory = HLAExecutorFactory(tx, bindings)

        class TwoPort(RecordingReceiver):
            def __init__(self):
                super().__init__(name="rcv", in_port="in_a")
                self.insert_input_port("in_b")

        m = TwoPort()
        sys_exec.register_entity(m)
        ex = sys_exec.model_map["rcv"][0]

        ex._on_rti_event("interaction", "A", [{"x": 1}], timestamp=0.0)
        ex._on_rti_event("interaction", "B", [{"y": 2}], timestamp=0.0)
        sys_exec.step(0.0)

        ports = sorted(p for p, _ in m.received)
        assert ports == ["in_a", "in_b"], (
            "§6: both inbound events at the same instant must be delivered "
            "before next round"
        )

    def test_M4_4_event_at_future_within_grant_delivered_in_later_round(self):
        sys_exec, tx = _build_one_receiver()
        counter = ConfluentCounter(name="counter", deadline=10.0)
        sys_exec.register_entity(counter)
        ex = sys_exec.model_map["counter"][0]

        # Inject at t=2 with grant=5: event must be processed within step.
        ex._on_rti_event("interaction", "Comm.X", [{"v": 1}], timestamp=2.0)
        sys_exec.step(5.0)

        assert counter.n_ext == 1, (
            "§6: events with timestamps within the grant window must fire "
            "in the corresponding round of step()"
        )
        assert sys_exec.global_time == 5.0, (
            "post-step global_time equals granted_time per §5.3 / system_executor.py:781"
        )

    def test_M4_5_event_beyond_grant_deferred_to_next_step(self):
        sys_exec, tx = _build_one_receiver()
        counter = ConfluentCounter(name="counter", deadline=100.0)
        sys_exec.register_entity(counter)
        ex = sys_exec.model_map["counter"][0]

        # Inject at t=10 but only grant up to t=5.
        ex._on_rti_event("interaction", "Comm.X", [{"v": 1}], timestamp=10.0)
        sys_exec.step(5.0)
        assert counter.n_ext == 0, (
            "§6: events beyond the grant must NOT fire this step"
        )

        sys_exec.step(15.0)
        assert counter.n_ext == 1, (
            "§6: deferred event fires once the grant covers its timestamp"
        )
