"""RTI-agnostic interface: RTIConnector template, codec, registry.

These tests pin the contract that lets *any* RTI plug into pyjevsim:

  * A backend only implements ``_do_send`` + ``_do_request_time_advance``
    (and optional lifecycle hooks); the base class supplies direction
    enforcement, codec (de)serialization, single-callback dispatch, the
    join/resign state machine, and idempotent close.
  * Codecs are invoked on the send/receive boundary and are orthogonal to
    the transport.
  * The registry selects a backend by name without importing its class.
  * A custom backend works end-to-end through HLAExecutorFactory +
    Federate exactly like LoopbackTransport.
"""

from __future__ import annotations

import pytest

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla import (
    Federate,
    HLAExecutorFactory,
    HLAInteraction,
    IdentityCodec,
    RTICapabilities,
    RTIConnector,
    available_rtis,
    create_rti,
    register_rti,
    unregister_rti,
)

from .conftest import EmitOnce


# --------------------------------------------------------- a minimal backend


class _MiniRTI(RTIConnector):
    """Smallest possible backend: in-memory mirror + recorded lifecycle.

    Demonstrates that a new RTI needs only the two abstract hooks; the
    lifecycle/codec/dispatch plumbing comes from RTIConnector.
    """

    capabilities = RTICapabilities(
        name="mini", time_management=True, timestamp_ordered=True,
        interactions=True, object_attributes=True, default_lookahead=1.0,
    )

    def __init__(self, codec=None):
        super().__init__(codec)
        self.sent = []
        self.lifecycle = []

    def _do_send(self, binding, wire, timestamp):
        self.sent.append((binding.fom_id, wire, timestamp))
        # Mirror out→in so subscribers see it (like loopback).
        self._emit(binding.kind, binding.fom_id, wire, timestamp)

    def _do_request_time_advance(self, target):
        return target

    def _do_join(self, federation, federate_name, fom_paths):
        self.lifecycle.append(("join", federation, federate_name))

    def _do_publish(self, binding):
        self.lifecycle.append(("publish", binding.fom_id))

    def _do_subscribe(self, binding):
        self.lifecycle.append(("subscribe", binding.fom_id))

    def _do_resign(self):
        self.lifecycle.append(("resign",))

    def _do_close(self):
        self.lifecycle.append(("close",))


# --------------------------------------------------------------- base class


class TestRTIConnectorTemplate:
    def test_direction_guard_blocks_inbound_send(self):
        rti = _MiniRTI()
        rti.send(HLAInteraction("X", direction="in"), [{"a": 1}])
        assert rti.sent == [], "an 'in' binding handed to send must be dropped"

    def test_send_emits_to_callback(self):
        rti = _MiniRTI()
        seen = []
        rti.on_receive(lambda *a: seen.append(a))
        rti.send(HLAInteraction("Comm.Chat", direction="out"), [{"t": "hi"}], timestamp=4.0)
        assert rti.sent == [("Comm.Chat", [{"t": "hi"}], 4.0)]
        assert seen == [("interaction", "Comm.Chat", [{"t": "hi"}], 4.0)]

    def test_publish_before_join_raises(self):
        rti = _MiniRTI()
        with pytest.raises(RuntimeError):
            rti.publish(HLAInteraction("X", direction="out"))
        with pytest.raises(RuntimeError):
            rti.subscribe(HLAInteraction("X", direction="in"))

    def test_join_twice_raises(self):
        rti = _MiniRTI()
        rti.join("Fed", "a", [])
        with pytest.raises(RuntimeError):
            rti.join("Fed", "a", [])

    def test_lifecycle_state_machine(self):
        rti = _MiniRTI()
        assert rti.joined is False
        rti.join("Fed", "a", ["f.xml"])
        assert rti.joined is True
        rti.publish(HLAInteraction("X", direction="out"))
        rti.subscribe(HLAInteraction("Y", direction="in"))
        rti.resign()
        assert rti.joined is False
        assert rti.lifecycle == [
            ("join", "Fed", "a"),
            ("publish", "X"),
            ("subscribe", "Y"),
            ("resign",),
        ]

    def test_close_is_idempotent_and_auto_resigns(self):
        rti = _MiniRTI()
        rti.join("Fed", "a", [])
        rti.close()
        rti.close()  # second call must be a no-op
        assert rti.lifecycle.count(("resign",)) == 1
        assert rti.lifecycle.count(("close",)) == 1


# ------------------------------------------------------------------- codec


class TestCodec:
    def test_custom_codec_round_trips(self):
        class _UpperCodec(IdentityCodec):
            def encode(self, binding, payload):
                return [str(p).upper() for p in payload]

            def decode(self, kind, fom_id, wire):
                return wire  # already encoded by the mirror

        rti = _MiniRTI(codec=_UpperCodec())
        seen = []
        rti.on_receive(lambda *a: seen.append(a))
        rti.send(HLAInteraction("X", direction="out"), ["hi", "yo"])
        # encode ran on the way out; mirror carried the encoded wire back.
        assert rti.sent[0][1] == ["HI", "YO"]
        assert seen[0][2] == ["HI", "YO"]


# ---------------------------------------------------------------- registry


class TestRegistry:
    def test_loopback_is_registered_by_default(self):
        assert "loopback" in available_rtis()
        t = create_rti("loopback")
        assert isinstance(t, RTIConnector)

    def test_register_and_create_custom(self):
        register_rti("mini-test", lambda **kw: _MiniRTI(**kw), replace=True)
        try:
            assert "mini-test" in available_rtis()
            t = create_rti("mini-test")
            assert isinstance(t, _MiniRTI)
            assert t.capabilities.name == "mini"
        finally:
            unregister_rti("mini-test")

    def test_duplicate_registration_rejected(self):
        register_rti("dup", lambda **kw: _MiniRTI(**kw), replace=True)
        try:
            with pytest.raises(ValueError):
                register_rti("dup", lambda **kw: _MiniRTI(**kw))
        finally:
            unregister_rti("dup")

    def test_unknown_backend_raises_with_listing(self):
        with pytest.raises(KeyError):
            create_rti("no-such-rti")


# -------------------------------------------------------------- end-to-end


def test_custom_backend_works_through_federate():
    """A custom RTIConnector drives a full federate exactly like loopback:
    output on a bound port reaches the RTI and mirrors back to a
    subscribed model via the normal HLAExecutor/router/insert path."""
    rti = _MiniRTI()
    sys_exec = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)

    bindings = {"out": HLAInteraction("Comm.Ping", direction="out")}
    sys_exec.exec_factory = HLAExecutorFactory(rti, {"emitter": bindings})
    sys_exec.register_entity(EmitOnce("emitter", payload={"ping": 1}))

    fed = Federate(sys_exec, rti)
    fed.join("Fed", "emitter", fom_paths=["f.xml"])
    fed.publish(bindings["out"])
    fed.run_until(end_time=3.0, lookahead=1.0)
    fed.resign()

    assert rti.sent, "the bound output must have been shipped to the RTI"
    assert rti.sent[0][0] == "Comm.Ping"
    assert ("join", "Fed", "emitter") in rti.lifecycle
