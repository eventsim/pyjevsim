"""M2 — HLAExecutorFactory + SysExecutor integration.

Spec section: docs/hla/specification.md §4.
Acceptance IDs: M2.1 .. M2.6.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pyjevsim.hla.factory")

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.behavior_executor import BehaviorExecutor
from pyjevsim.executor_factory import ExecutorFactory
from pyjevsim.hla.bindings import HLAInteraction
from pyjevsim.hla.factory import HLAExecutorFactory
from pyjevsim.hla.hla_executor import HLAExecutor
from pyjevsim.hla.transport import LoopbackTransport

from .conftest import EmitOnce, RecordingReceiver


def _sys():
    return SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)


class TestFactoryShape:
    def test_M2_1_subclass_of_executor_factory(self):
        assert issubclass(HLAExecutorFactory, ExecutorFactory), (
            "§4.1: HLAExecutorFactory inherits from ExecutorFactory"
        )

    def test_M2_2_model_with_bindings_yields_hla_executor(self):
        tx = LoopbackTransport()
        bindings_by_model = {
            "alice": {"out": HLAInteraction("X", direction="out")},
        }
        f = HLAExecutorFactory(tx, bindings_by_model)
        sys_exec = _sys()
        ex = f.create_behavior_executor(
            None, 0, float("inf"), "default", EmitOnce(name="alice"), sys_exec
        )
        assert isinstance(ex, HLAExecutor), (
            "§4.1: model in bindings_by_model must produce HLAExecutor"
        )

    def test_M2_3_model_without_bindings_yields_plain_behavior_executor(self):
        tx = LoopbackTransport()
        f = HLAExecutorFactory(tx, bindings_by_model={})
        sys_exec = _sys()
        ex = f.create_behavior_executor(
            None, 0, float("inf"), "default", EmitOnce(name="bob"), sys_exec
        )
        assert isinstance(ex, BehaviorExecutor), (
            "§4.1: not-bound model produces plain BehaviorExecutor"
        )
        assert not isinstance(ex, HLAExecutor)


class TestSysExecutorWiring:
    def test_M2_4_register_entity_uses_replaced_factory(self):
        tx = LoopbackTransport()
        sys_exec = _sys()
        bindings_by_model = {
            "alice": {"out": HLAInteraction("X", direction="out")},
        }
        sys_exec.exec_factory = HLAExecutorFactory(tx, bindings_by_model)

        sys_exec.register_entity(EmitOnce(name="alice"))
        sys_exec.register_entity(EmitOnce(name="bob"))

        alice_exec = sys_exec.model_map["alice"][0]
        bob_exec = sys_exec.model_map["bob"][0]
        assert isinstance(alice_exec, HLAExecutor), (
            "§4.2: factory swap is the public wiring path"
        )
        assert isinstance(bob_exec, BehaviorExecutor)
        assert not isinstance(bob_exec, HLAExecutor)


class TestEndToEndStep:
    def test_M2_5_step_delivers_bound_output_to_transport(self):
        tx = LoopbackTransport()
        seen: list = []
        tx.on_receive(lambda kind, fom, payload, ts: seen.append((fom, payload)))

        sys_exec = _sys()
        bindings_by_model = {
            "alice": {"out": HLAInteraction("Comm.Chat", direction="out")},
        }
        sys_exec.exec_factory = HLAExecutorFactory(tx, bindings_by_model)
        sys_exec.register_entity(EmitOnce(name="alice"))

        sys_exec.step(0.0)

        assert seen == [("Comm.Chat", [{"hello": "world"}])], (
            "§3.2 + §4: emitter's output should reach transport on step"
        )

    def test_M2_6_two_models_cross_wired_via_loopback(self):
        # Two SysExecutors? No — single sys_exec, two models, one transport,
        # bindings cross-mapped: alice OUT → bob IN.
        tx = LoopbackTransport()
        sys_exec = _sys()

        bindings = {
            "alice": {"out": HLAInteraction("Comm.Chat", direction="out")},
            "bob": {"in": HLAInteraction("Comm.Chat", direction="in")},
        }
        sys_exec.exec_factory = HLAExecutorFactory(tx, bindings)

        receiver = RecordingReceiver(name="bob", in_port="in")
        sys_exec.register_entity(EmitOnce(name="alice"))
        sys_exec.register_entity(receiver)

        # First step — alice emits, transport mirrors to bob's inbound queue.
        sys_exec.step(0.0)
        # Second step — bob picks up the queued external event.
        sys_exec.step(1.0)

        assert receiver.received, (
            "§4: end-to-end loopback must deliver alice's output to bob.ext_trans"
        )
        port, payload = receiver.received[0]
        assert port == "in"
        assert payload == [{"hello": "world"}]
