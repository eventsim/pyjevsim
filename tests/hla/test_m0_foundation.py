"""M0 — Foundation: bindings dataclasses + Transport Protocol + LoopbackTransport.

Spec section: docs/hla/specification.md §1, §2.
Acceptance IDs: M0.1 .. M0.8.

The whole file skips until ``pyjevsim.hla`` is importable. Once M0 is
implemented the imports succeed and these tests run.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pyjevsim.hla.bindings")
pytest.importorskip("pyjevsim.hla.transport")

from pyjevsim.hla.bindings import HLAAttribute, HLAInteraction
from pyjevsim.hla.transport import LoopbackTransport, Transport


# ----------------------------------------------------------------- bindings


class TestBindings:
    def test_M0_1_interaction_is_frozen_and_hashable(self):
        a = HLAInteraction(fom_id="X")
        with pytest.raises(Exception):
            a.fom_id = "Y"  # type: ignore[misc]
        # Must be hashable (used as dict key in HLAExecutor's inbound routes).
        {a: 1}

    def test_M0_1_attribute_is_frozen_and_hashable(self):
        a = HLAAttribute(fom_id="X", object_class="C")
        with pytest.raises(Exception):
            a.fom_id = "Y"  # type: ignore[misc]
        {a: 1}

    def test_M0_1_equality_by_value(self):
        assert HLAInteraction("X") == HLAInteraction("X")
        assert HLAAttribute("X", object_class="C") == HLAAttribute(
            "X", object_class="C"
        )
        assert HLAInteraction("X") != HLAInteraction("Y")

    def test_M0_2_interaction_defaults(self):
        a = HLAInteraction(fom_id="X")
        assert a.direction == "out", "§1.1: default direction is 'out'"
        assert a.kind == "interaction", "§1.1: kind is 'interaction'"

    def test_M0_3_attribute_defaults(self):
        a = HLAAttribute(fom_id="X", object_class="Vehicle")
        assert a.direction == "out"
        assert a.kind == "attribute", "§1.2: kind is 'attribute'"
        assert a.object_class == "Vehicle"

    def test_M0_3_inbound_attribute_allows_no_object_class(self):
        # For inbound reflects the transport resolves the class from the
        # wire payload (§1.2). The dataclass must accept None.
        a = HLAAttribute(fom_id="X", direction="in")
        assert a.object_class is None


# ----------------------------------------------------------------- transport


class TestTransportProtocol:
    def test_M0_4_protocol_has_required_methods(self):
        # A Protocol can't be instantiated; we just check the names exist.
        for name in ("send", "on_receive", "request_time_advance", "close"):
            assert hasattr(Transport, name), f"§2.1: Transport must define {name}"


class TestLoopbackTransport:
    def test_M0_5_send_invokes_callback_with_mirrored_binding(self):
        tx = LoopbackTransport()
        seen: list[tuple] = []
        tx.on_receive(lambda kind, fom_id, payload, ts: seen.append(
            (kind, fom_id, payload, ts)
        ))

        out_binding = HLAInteraction("Communication.ChatMsg", direction="out")
        # §2.1: payload is always a list (the result of SysMessage.retrieve()).
        tx.send(out_binding, [{"text": "hi"}])

        assert len(seen) == 1, "§2.2: send must invoke callback exactly once"
        kind, fom_id, payload, _ts = seen[0]
        assert kind == "interaction"
        assert fom_id == "Communication.ChatMsg"
        assert payload == [{"text": "hi"}], "§2.1: payload is forwarded as-is (list)"

    def test_M0_6_no_callback_no_op(self):
        tx = LoopbackTransport()
        # No on_receive registered. Must not raise.
        tx.send(HLAInteraction("X", direction="out"), [{"a": 1}])

    def test_M0_6_drops_inbound_when_direction_in(self):
        # §2.2: Loopback rewrites direction. Sending an "in" binding makes
        # no sense — must not call back.
        tx = LoopbackTransport()
        seen: list = []
        tx.on_receive(lambda *a: seen.append(a))
        tx.send(HLAInteraction("X", direction="in"), [{"a": 1}])
        assert seen == [], (
            "§2.2: send on direction='in' must not deliver "
            "(loopback only mirrors out→in)"
        )

    def test_M0_7_request_time_advance_is_identity(self):
        tx = LoopbackTransport()
        assert tx.request_time_advance(0.0) == 0.0
        assert tx.request_time_advance(3.5) == 3.5

    def test_M0_8_close_is_idempotent(self):
        tx = LoopbackTransport()
        tx.close()
        tx.close()  # second call must not raise


# --------------------------------------------------------------------- router


# Router tests live in this file because the router is part of M0
# (specification.md §2.3, task T0.5). They depend on LoopbackTransport.

pytest.importorskip("pyjevsim.hla.transport", reason="router lives here")
from pyjevsim.hla.transport import _HLARouter   # noqa: E402


class _StubExecutor:
    """Minimal stand-in for HLAExecutor — only exposes _on_rti_event."""
    def __init__(self, name="stub"):
        self.name = name
        self.received: list[tuple] = []
    def _on_rti_event(self, kind, fom_id, payload, timestamp):
        self.received.append((kind, fom_id, payload, timestamp))


class TestHLARouter:
    def test_subscribed_executor_receives_event(self):
        tx = LoopbackTransport()
        router = _HLARouter(tx)
        ex = _StubExecutor("alice")
        router.subscribe("interaction", "Comm.Chat", ex)

        tx.send(HLAInteraction("Comm.Chat", direction="out"), [{"text": "hi"}])

        assert ex.received == [
            ("interaction", "Comm.Chat", [{"text": "hi"}], None)
        ], "§2.3: subscribed executor must receive matching events"

    def test_unrelated_executor_does_not_receive(self):
        tx = LoopbackTransport()
        router = _HLARouter(tx)
        alice = _StubExecutor("alice")
        bob = _StubExecutor("bob")
        router.subscribe("interaction", "Comm.A", alice)
        router.subscribe("interaction", "Comm.B", bob)

        tx.send(HLAInteraction("Comm.A", direction="out"), [{"k": 1}])

        assert len(alice.received) == 1
        assert bob.received == [], (
            "§2.3: only executors subscribed to (kind, fom_id) receive"
        )

    def test_unsubscribe_stops_delivery(self):
        tx = LoopbackTransport()
        router = _HLARouter(tx)
        ex = _StubExecutor("alice")
        router.subscribe("interaction", "Comm.X", ex)
        router.unsubscribe("interaction", "Comm.X", ex)

        tx.send(HLAInteraction("Comm.X", direction="out"), [{"k": 1}])

        assert ex.received == [], "§2.3: unsubscribe must stop delivery"
