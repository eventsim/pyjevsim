"""Portico backend tests.

The hermetic cases (registration, the IEEE 1516-2010 ``HLAunicodeString``
codec, the three-sub-step time axis) need neither Java nor an RTI. The live
case needs a Portico distribution and is skipped without one.

Verified live against **Portico 2.1.4** with **Temurin 11** and JPype 1.7.1::

    set PYJEVSIM_JVM=C:\\Program Files\\Eclipse Adoptium\\jdk-11...\\bin\\server\\jvm.dll
    set PYJEVSIM_JAR=C:\\...\\portico-2.1.4\\lib\\portico.jar
    set RTI_HOME=C:\\...\\portico-2.1.4
    set PYJEVSIM_PORTICO_LIVE=1
    pytest tests/hla/test_portico_backend.py
"""

from __future__ import annotations

import os
import struct
import threading

import pytest

from pyjevsim.hla.backends.pitch import PitchTransport
from pyjevsim.hla.transport import IdentityCodec
from pyjevsim.hla.backends.portico import (
    PorticoTransport,
    decode_unicode_string,
    encode_unicode_string,
)

JAR = os.environ.get("PYJEVSIM_JAR", "")
JVM = os.environ.get("PYJEVSIM_JVM")
LIVE = os.environ.get("PYJEVSIM_PORTICO_LIVE") == "1"
FOM = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "examples", "hla_pingpong", "fom", "PingPong.xml"))


def _live_ok() -> bool:
    if not (LIVE and JAR and os.path.exists(JAR)):
        return False
    try:
        import jpype  # noqa: F401
    except Exception:
        return False
    return True


requires_live = pytest.mark.skipif(
    not _live_ok(),
    reason="set PYJEVSIM_PORTICO_LIVE=1 with PYJEVSIM_JAR=<portico.jar>",
)


# ------------------------------------------------------------- registration


def test_portico_backend_is_registered():
    """Always runs: the backend self-registers even without JPype."""
    from pyjevsim.hla import available_rtis
    assert "portico" in available_rtis()


def test_portico_import_does_not_require_jpype():
    """Importing the module must not pull in JPype (lazy dependency)."""
    import importlib
    mod = importlib.import_module("pyjevsim.hla.backends.portico")
    assert issubclass(mod.PorticoTransport, PitchTransport)


def test_portico_advertises_receive_order():
    """Portico does not deliver reflections TSO; callers must be told."""
    assert PorticoTransport.capabilities.name == "portico"
    assert PorticoTransport.capabilities.time_management is True
    assert PorticoTransport.capabilities.timestamp_ordered is False


# ------------------------------------------------------ HLAunicodeString codec


@pytest.mark.parametrize("value", ["", "ping", "blue_ship_0::decoy_3", "\u00e9\u4e2d"])
def test_unicode_string_round_trip(value):
    assert decode_unicode_string(encode_unicode_string(value)) == value


def test_unicode_string_octets_match_the_standard():
    """4-octet big-endian code-unit count, then UTF-16BE code units."""
    raw = encode_unicode_string("abc")
    assert raw == struct.pack(">I", 3) + "abc".encode("utf-16-be")
    assert len(raw) == 4 + 2 * 3          # no padding, unlike Portico's own


def test_unicode_string_counts_code_units_not_characters():
    """A non-BMP character is two UTF-16 code units."""
    raw = encode_unicode_string("\U0001F600")
    assert struct.unpack(">I", raw[:4])[0] == 2
    assert decode_unicode_string(raw) == "\U0001F600"


def test_unicode_string_rejects_a_truncated_buffer():
    raw = encode_unicode_string("ping")
    with pytest.raises(ValueError):
        decode_unicode_string(raw[:-2])
    with pytest.raises(ValueError):
        decode_unicode_string(b"\x00\x00")


# ------------------------------------------------------- sub-tick time axis


class _NoJVM(PorticoTransport):
    """PorticoTransport with the JPype/RTI half of __init__ skipped."""

    def __init__(self):
        self._settle = 0.0
        self._quiet = 0.0
        self._inbox = []
        self._inbox_lock = threading.Lock()
        self._rx_count = 0
        self._logical_time = 0.0
        self._lookahead = 1.0
        self._callback = None
        self._codec = IdentityCodec()


def test_rti_time_axis_is_three_sub_steps_per_tick():
    tx = _NoJVM()
    assert tx._rti_time(0.0) == 0.0
    assert tx._rti_time(2.0) == 6.0
    assert tx._rti_lookahead() == 1.0     # one sub-step, not one tick


def test_time_advance_settles_before_the_release_sub_step(monkeypatch):
    """The wait for reflections sits between the sync and release steps."""
    events = []
    monkeypatch.setattr(
        PitchTransport, "_do_request_time_advance",
        lambda self, target: (events.append(target), target)[1],
    )
    monkeypatch.setattr(_NoJVM, "_settle_inbound",
                        lambda self: events.append("settle"))
    monkeypatch.setattr(_NoJVM, "_release_inbox",
                        lambda self: events.append("release"))
    tx = _NoJVM()
    for t in (1.0, 2.0, 3.0):
        assert tx._do_request_time_advance(t) == t      # caller ticks, not RTI time
        assert tx._logical_time == t
    assert events == [3.0, 4.0, "settle", "release", 5.0,
                      6.0, 7.0, "settle", "release", 8.0,
                      9.0, 10.0, "settle", "release", 11.0]


def test_reflections_are_invisible_until_the_inbox_is_released():
    """Nothing reaches the models until the transport says so."""
    seen = []
    tx = _NoJVM()
    tx.on_receive(lambda *a: seen.append(a))
    tx._emit("attribute", "X.Y", [{"v": 1}], 3.0)
    tx._emit("attribute", "X.Y", [{"v": 2}], 3.0)
    assert seen == []                       # buffered, not delivered
    tx._release_inbox()
    assert seen == [("attribute", "X.Y", [{"v": 1}], 3.0),
                    ("attribute", "X.Y", [{"v": 2}], 3.0)]   # arrival order
    tx._release_inbox()
    assert len(seen) == 2                   # drained, not replayed


def test_settle_returns_once_the_inbound_stream_is_idle():
    tx = _NoJVM()
    tx._settle, tx._quiet = 5.0, 0.01     # cap far above the idle threshold
    import time as _t
    started = _t.monotonic()
    tx._settle_inbound()
    assert _t.monotonic() - started < 1.0  # left early, nowhere near the cap


# -------------------------------------------------------------- live Portico


@requires_live
def test_live_join_publish_subscribe_resign():
    """End-to-end against a real Portico LRC: no CRC process is needed."""
    from pyjevsim.hla import create_rti
    from pyjevsim.hla.bindings import HLAInteraction

    fom_map = {"PingPong.Ping": {"kind": "interaction",
                                 "class": "HLAinteractionRoot.Ping",
                                 "fields": {"count": "int32",
                                            "sender": "string"}}}
    ping = HLAInteraction("PingPong.Ping", direction="inout")
    tx = create_rti("portico", federation="PorticoSmoke", federate="smoke",
                    fom=FOM, fom_map=fom_map, jvm_path=JVM, classpath=[JAR],
                    lookahead=1.0, settle=0.0)
    try:
        tx.join("PorticoSmoke", "smoke", fom_paths=[FOM])
        assert tx.joined
        tx.publish(ping)
        tx.subscribe(ping)
        assert tx.request_time_advance(1.0) == 1.0
    finally:
        tx.resign()
