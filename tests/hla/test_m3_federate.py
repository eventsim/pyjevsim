"""M3 — Federate runtime + HLA_TIME grant loop.

Spec section: docs/hla/specification.md §5.
Acceptance IDs: M3.1 .. M3.9.

These tests use a stub transport instead of LoopbackTransport so we can
observe and steer time-advance grants directly.
"""

from __future__ import annotations

from typing import Callable

import pytest

pytest.importorskip("pyjevsim.hla.federate")

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla.bindings import HLAInteraction
from pyjevsim.hla.factory import HLAExecutorFactory
from pyjevsim.hla.federate import Federate
from pyjevsim.hla.transport import Transport

from .conftest import EmitOnce


# ----------------------------------------------------------- stub transport


class StubTransport:
    """Records lifecycle calls and lets the test steer grant returns."""

    def __init__(self, grant_fn: Callable[[float], float] | None = None):
        self.sent: list = []
        self.callback: Callable | None = None
        self.published: list = []
        self.subscribed: list = []
        self.joined = False
        self.resigned = False
        self.grants: list[tuple[float, float]] = []   # (target, granted)
        self._grant_fn = grant_fn or (lambda t: t)
        self.closed = False

    # Transport surface
    def send(self, binding, payload):
        self.sent.append((binding, payload))

    def on_receive(self, cb):
        self.callback = cb

    def request_time_advance(self, target):
        granted = self._grant_fn(target)
        self.grants.append((target, granted))
        return granted

    def close(self):
        self.closed = True

    # Lifecycle helpers — Federate delegates to these.
    def join(self, federation, federate_name, fom_paths):
        self.joined = True

    def publish(self, binding):
        self.published.append(binding)

    def subscribe(self, binding):
        self.subscribed.append(binding)

    def resign(self):
        self.resigned = True


# --------------------------------------------------------------- helpers


def _sys():
    return SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)


def _wire(sys_exec, transport, bindings_by_model=None):
    sys_exec.exec_factory = HLAExecutorFactory(
        transport, bindings_by_model or {}
    )


# -------------------------------------------------------------- tests


class TestConstruction:
    def test_M3_1_constructs_without_io(self):
        tx = StubTransport()
        fed = Federate(_sys(), tx)
        assert tx.joined is False
        assert tx.published == []
        assert tx.subscribed == []


class TestLifecycleGuards:
    def test_M3_2_publish_before_join_raises(self):
        tx = StubTransport()
        fed = Federate(_sys(), tx)
        with pytest.raises(RuntimeError):
            fed.publish(HLAInteraction("X", direction="out"))

    def test_M3_3_subscribe_before_join_raises(self):
        tx = StubTransport()
        fed = Federate(_sys(), tx)
        with pytest.raises(RuntimeError):
            fed.subscribe(HLAInteraction("X", direction="in"))

    def test_M3_4_join_publish_subscribe_resign_round_trip(self):
        tx = StubTransport()
        fed = Federate(_sys(), tx)

        fed.join("Fed", "alice", fom_paths=["a.xml"])
        fed.publish(HLAInteraction("X", direction="out"))
        fed.subscribe(HLAInteraction("Y", direction="in"))
        fed.resign()

        assert tx.joined is True
        assert len(tx.published) == 1
        assert len(tx.subscribed) == 1
        assert tx.resigned is True


class TestRunUntil:
    def test_M3_5_calls_request_time_advance_each_step(self):
        tx = StubTransport()
        sys_exec = _sys()
        fed = Federate(sys_exec, tx)
        fed.join("Fed", "f", fom_paths=[])
        fed.run_until(end_time=10.0, lookahead=1.0)
        # 10 grants of 1.0 → reaches 10.0.
        assert len(tx.grants) == 10, (
            "§5.3: one request_time_advance per loop iteration"
        )
        targets = [t for t, _ in tx.grants]
        assert targets == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    def test_M3_6_step_called_per_grant(self):
        tx = StubTransport()
        sys_exec = _sys()

        steps: list[float] = []
        original_step = sys_exec.step
        def spy(t):
            steps.append(t)
            return original_step(t)
        sys_exec.step = spy  # type: ignore[assignment]

        fed = Federate(sys_exec, tx)
        fed.join("Fed", "f", fom_paths=[])
        fed.run_until(end_time=3.0, lookahead=1.0)
        assert steps == [1.0, 2.0, 3.0]

    def test_M3_7_terminates_when_grant_reaches_end_time(self):
        tx = StubTransport()
        sys_exec = _sys()
        fed = Federate(sys_exec, tx)
        fed.join("Fed", "f", fom_paths=[])
        fed.run_until(end_time=2.0, lookahead=10.0)   # one grant covers it
        assert sys_exec.global_time >= 2.0
        # target is min(0+10, 2)=2 ⇒ exactly one iteration.
        assert len(tx.grants) == 1

    def test_M3_8_lookahead_must_be_positive(self):
        tx = StubTransport()
        fed = Federate(_sys(), tx)
        fed.join("Fed", "f", fom_paths=[])
        with pytest.raises(ValueError):
            fed.run_until(end_time=1.0, lookahead=0.0)
        with pytest.raises(ValueError):
            fed.run_until(end_time=1.0, lookahead=-1.0)

    def test_M3_9_capped_grants_advance_correctly(self):
        # Transport caps every grant at 0.5 — we should still reach 2.0.
        capped = StubTransport(grant_fn=lambda t: min(t, 0.5))

        # Caveat: with this stub the granted time is always 0.5 on iter
        # 1 → global_time = 0.5; iter 2 target = 1.5, granted = 0.5 →
        # global_time stays at 0.5 → infinite loop. So instead make the
        # grant strictly monotonic but partial.
        state = {"t": 0.0}
        def partial_grant(target):
            state["t"] = min(target, state["t"] + 0.5)
            return state["t"]

        tx = StubTransport(grant_fn=partial_grant)
        sys_exec = _sys()
        fed = Federate(sys_exec, tx)
        fed.join("Fed", "f", fom_paths=[])
        fed.run_until(end_time=2.0, lookahead=1.0)
        assert sys_exec.global_time >= 2.0, (
            "§5.3: loop terminates when global_time >= end_time"
        )
