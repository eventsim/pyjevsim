"""Offline tests for the optional native GORTI backend."""

from __future__ import annotations

import ast
import builtins
from types import SimpleNamespace

import pytest

from pyjevsim.hla import available_rtis, create_rti
from pyjevsim.hla.bindings import HLAAttribute, HLAInteraction
from pyjevsim.hla.transport import RTIConnector
from pyjevsim.hla.backends import gorti


FOM_MAP = {
    "Chat.Message": {
        "kind": "interaction",
        "class": "HLAinteractionRoot.Message",
        "fields": {"count": "int32", "sender": "string"},
    },
    "Vehicle.state": {
        "kind": "attribute",
        "class": "HLAobjectRoot.Vehicle",
        "fields": {"position": "float64", "name": "string"},
    },
}


class _AlreadyExists(Exception):
    pass


class _TypedHandle(int):
    def __repr__(self):
        return f"TypedHandle({int(self)})"


class _LiteralCodec:
    def __init__(self, spec) -> None:
        self.spec = spec

    def encode(self, value):
        return repr(value).encode("utf-8")

    def decode(self, data, offset=0):
        assert offset == 0
        return ast.literal_eval(bytes(data).decode("utf-8")), len(data)


class _FakeAmbassador:
    instances = []

    def __init__(self) -> None:
        type(self).instances.append(self)
        self.callback = None
        self.calls = []
        self._next_handle = 10
        self._handles = {}
        self.raise_already_exists = False

    def _handle(self, *key):
        if key not in self._handles:
            self._handles[key] = _TypedHandle(self._next_handle)
            self._next_handle += 1
        return self._handles[key]

    def connect(self, callback, url):
        self.callback = callback
        self.calls.append(("connect", url))

    def disconnect(self):
        self.calls.append(("disconnect",))

    def createFederationExecution(self, federation, modules):
        self.calls.append(("create", federation, list(modules)))
        if self.raise_already_exists:
            raise _AlreadyExists(federation)

    def destroyFederationExecution(self, federation):
        self.calls.append(("destroy", federation))

    def joinFederationExecution(self, federate, federation, modules):
        self.calls.append(("join", federate, federation, list(modules)))

    def resignFederationExecution(self, action):
        self.calls.append(("resign", action))

    def enableTimeRegulation(self, lookahead):
        self.calls.append(("regulating", lookahead))

    def enableTimeConstrained(self):
        self.calls.append(("constrained",))

    def getInteractionClassHandle(self, class_name):
        return self._handle("interaction", class_name)

    def getParameterHandle(self, class_handle, field):
        return self._handle("parameter", class_handle, field)

    def getObjectClassHandle(self, class_name):
        return self._handle("object", class_name)

    def getAttributeHandle(self, class_handle, field):
        return self._handle("attribute", class_handle, field)

    def publishInteractionClass(self, class_handle):
        self.calls.append(("publish_interaction", class_handle))

    def subscribeInteractionClass(self, class_handle):
        self.calls.append(("subscribe_interaction", class_handle))

    def publishObjectClassAttributes(self, class_handle, attributes):
        self.calls.append(("publish_object", class_handle, list(attributes)))

    def subscribeObjectClassAttributes(self, class_handle, attributes):
        self.calls.append(("subscribe_object", class_handle, list(attributes)))

    def registerObjectInstance(self, class_handle):
        handle = self._handle("instance", class_handle)
        self.calls.append(("register_object", class_handle, handle))
        return handle

    def sendInteraction(self, class_handle, parameters, timestamp=None):
        self.calls.append(
            ("send_interaction", class_handle, dict(parameters), timestamp)
        )

    def updateAttributeValues(self, object_handle, values, timestamp=None):
        self.calls.append(
            ("update_attributes", object_handle, dict(values), timestamp)
        )

    def timeAdvanceRequest(self, target):
        self.calls.append(("time_advance", target))
        self.callback.timeAdvanceGrant(target)


@pytest.fixture
def fake_sdk(monkeypatch):
    _FakeAmbassador.instances.clear()
    requested_codecs = []

    def codec_for(spec):
        requested_codecs.append(spec)
        return _LiteralCodec(spec)

    sdk = SimpleNamespace(
        FederationExecutionAlreadyExists=_AlreadyExists,
        Rti1516eAmbassador=_FakeAmbassador,
        codec_for=codec_for,
    )
    monkeypatch.setattr(gorti, "_load_sdk", lambda: sdk)
    return sdk, requested_codecs


def _transport(**kwargs):
    return create_rti(
        "gorti",
        federation="Demo",
        federate="alice",
        fom="Demo.xml",
        fom_map=FOM_MAP,
        url="memory://unit-test",
        **kwargs,
    )


def test_gorti_backend_is_registered_without_importing_the_sdk():
    assert "gorti" in available_rtis()
    assert issubclass(gorti.GortiTransport, RTIConnector)
    assert "rti1516e" not in gorti.__dict__


def test_missing_sdk_error_explains_the_optional_install(monkeypatch):
    real_import = builtins.__import__

    def without_gorti(name, *args, **kwargs):
        if name == "rti1516e" or name.startswith("rti1516e."):
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_gorti)
    with pytest.raises(ImportError, match=r"pip install -e <gorti>/pysdk"):
        gorti._load_sdk()


def test_create_join_and_declarations_reuse_pitch_fom_map(fake_sdk):
    tx = _transport(lookahead=0.25)
    amb = _FakeAmbassador.instances[-1]
    amb.raise_already_exists = True

    interaction = HLAInteraction("Chat.Message", direction="inout")
    attribute = HLAAttribute("Vehicle.state", direction="inout")
    tx.join("Demo", "alice", ["Demo.xml"])
    tx.publish(interaction)
    tx.subscribe(interaction)
    tx.publish(attribute)
    tx.subscribe(attribute)

    assert ("connect", "memory://unit-test") in amb.calls
    assert ("create", "Demo", ["Demo.xml"]) in amb.calls
    assert ("join", "alice", "Demo", ["Demo.xml"]) in amb.calls
    assert ("regulating", 0.25) in amb.calls
    assert ("constrained",) in amb.calls
    assert any(call[0] == "publish_interaction" for call in amb.calls)
    assert any(call[0] == "subscribe_interaction" for call in amb.calls)
    assert any(call[0] == "publish_object" for call in amb.calls)
    assert any(call[0] == "subscribe_object" for call in amb.calls)
    assert any(call[0] == "register_object" for call in amb.calls)


def test_interaction_and_attribute_send_encode_fields_and_use_tso(fake_sdk):
    _sdk, requested_codecs = fake_sdk
    tx = _transport(lookahead=0.5)
    amb = _FakeAmbassador.instances[-1]
    interaction = HLAInteraction("Chat.Message", direction="out")
    attribute = HLAAttribute("Vehicle.state", direction="out")
    tx.join("Demo", "alice", ["Demo.xml"])
    tx.publish(interaction)
    tx.publish(attribute)

    tx.send(interaction, [{"count": 7, "sender": "alice"}], timestamp=2.0)
    assert tx.request_time_advance(4.0) == 4.0
    tx.send(attribute, [{"position": 3.25, "name": "car"}])

    interaction_call = next(c for c in amb.calls if c[0] == "send_interaction")
    assert interaction_call[3] == 2.0
    assert sorted(interaction_call[2].values()) == [b"'alice'", b"7"]
    update_call = next(c for c in amb.calls if c[0] == "update_attributes")
    assert update_call[3] == 4.5
    assert sorted(update_call[2].values()) == [b"'car'", b"3.25"]
    assert requested_codecs == [
        "HLAinteger32BE",
        "HLAunicodeString",
        "HLAfloat64BE",
    ]


def test_callbacks_decode_interactions_and_discovered_object_attributes(fake_sdk):
    tx = _transport()
    amb = _FakeAmbassador.instances[-1]
    interaction = HLAInteraction("Chat.Message", direction="in")
    attribute = HLAAttribute("Vehicle.state", direction="in")
    tx.join("Demo", "alice", ["Demo.xml"])
    tx.subscribe(interaction)
    tx.subscribe(attribute)
    received = []
    tx.on_receive(lambda *args: received.append(args))

    ic = tx._ic_handles["Chat.Message"]
    ph = tx._param_handles["Chat.Message"]
    # Mirror the gRPC callback fallback seen when the local FOM/MIM name
    # cache cannot resolve handles: parameter 1 is ``_payload`` and later
    # parameters use their numeric handle strings.
    ph["count"] = 1
    amb.callback.receiveInteraction(
        str(int(ic)),
        {
            "_payload": tx._field_codec.encode("int32", 9),
            str(ph["sender"]): tx._field_codec.encode("string", "bob"),
        },
        3.0,
    )

    oc = tx._oc_handles["Vehicle.state"]
    ah = tx._attr_handles["Vehicle.state"]
    amb.callback.discoverObjectInstance(99, str(oc), "car-99", object_class=oc)
    amb.callback.reflectAttributeValues(
        99,
        {},
        3.5,
        attribute_values={
            ah["position"]: tx._field_codec.encode("float64", 12.5),
            ah["name"]: tx._field_codec.encode("string", "peer"),
        },
    )

    assert received == [
        ("interaction", "Chat.Message", [{"count": 9, "sender": "bob"}], 3.0),
        (
            "attribute",
            "Vehicle.state",
            [{"position": 12.5, "name": "peer"}],
            3.5,
        ),
    ]

    amb.callback.removeObjectInstance(99, b"", 4.0)
    amb.callback.reflectAttributeValues(
        99,
        {},
        4.0,
        attribute_values={
            ah["position"]: tx._field_codec.encode("float64", 13.0)
        },
    )
    assert len(received) == 2


def test_federation_halt_releases_time_waiter_with_an_error(fake_sdk):
    tx = _transport()
    amb = _FakeAmbassador.instances[-1]

    def halt_instead_of_grant(target):
        amb.calls.append(("time_advance", target))
        amb.callback.federationHalted("stall", 42)

    amb.timeAdvanceRequest = halt_instead_of_grant
    with pytest.raises(RuntimeError, match="federation halted.*42"):
        tx.request_time_advance(5.0)


def test_close_resigns_deletes_objects_and_disconnects_once(fake_sdk):
    tx = _transport()
    amb = _FakeAmbassador.instances[-1]
    tx.join("Demo", "alice", ["Demo.xml"])

    tx.close()
    tx.close()

    assert amb.calls.count(("resign", "CANCEL_THEN_DELETE_THEN_DIVEST")) == 1
    assert amb.calls.count(("destroy", "Demo")) == 1
    assert amb.calls.count(("disconnect",)) == 1
    assert tx.joined is False


@pytest.mark.parametrize("lookahead", [0, -1])
def test_rejects_nonpositive_lookahead(fake_sdk, lookahead):
    with pytest.raises(ValueError, match="lookahead must be positive"):
        _transport(lookahead=lookahead)
