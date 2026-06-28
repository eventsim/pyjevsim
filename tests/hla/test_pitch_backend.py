"""Pitch pRTI backend tests — guarded; skip when the toolchain is absent.

These exercise the *real* PitchTransport against a live Pitch pRTI. They are
skipped automatically unless the full stack is available:

  * JPype importable AND able to start a JVM (needs Java >= 9 for JPype>=1.6);
  * ``prti1516e.jar`` discoverable (PRTI_HOME env var or the default install);
  * for the live-federation cases, the env var ``PYJEVSIM_PITCH_LIVE=1`` and a
    running CRC.

Verified live against **Pitch pRTI Free 5.5.2** with **Temurin 11** via::

    set PYJEVSIM_JVM=C:\\Program Files\\Eclipse Adoptium\\jdk-11...\\bin\\server\\jvm.dll
    set PYJEVSIM_PITCH_LIVE=1            # with a running CRC
    pytest tests/hla/test_pitch_backend.py

Without ``PYJEVSIM_JVM`` the default suite stays hermetic (these cases skip);
the protocol-level ping-pong behaviour is also covered deterministically by
tests/hla/test_pingpong.py against the in-process bus. The PitchTransport
remains importable regardless (its JPype import is lazy).
"""

from __future__ import annotations

import os
import sys

import pytest

PRTI_HOME = os.environ.get("PRTI_HOME", r"C:\Program Files\prti1516e")
JAR = os.path.join(PRTI_HOME, "lib", "prti1516e.jar")
FOM = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "examples", "hla_pingpong", "fom", "PingPong.xml"))

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "examples", "hla_pingpong")))


JVM = os.environ.get("PYJEVSIM_JVM")  # explicit Java>=9 jvm.dll (optional)


def _jvm_bootable() -> bool:
    try:
        import jpype
    except Exception:
        return False
    if not os.path.exists(JAR):
        return False
    try:
        if not jpype.isJVMStarted():
            if JVM:
                jpype.startJVM(JVM, classpath=[JAR])
            else:
                jpype.startJVM(classpath=[JAR])
        return True
    except Exception:
        return False


jvm_ok = _jvm_bootable()
live = os.environ.get("PYJEVSIM_PITCH_LIVE") == "1"

requires_jvm = pytest.mark.skipif(
    not jvm_ok,
    reason="JPype + Java>=9 + prti1516e.jar required (set PRTI_HOME)",
)
requires_live = pytest.mark.skipif(
    not (jvm_ok and live),
    reason="set PYJEVSIM_PITCH_LIVE=1 with a running CRC for live federation",
)


def test_pitch_backend_is_registered():
    """Always runs: the backend self-registers even without JPype."""
    from pyjevsim.hla import available_rtis
    assert "pitch" in available_rtis()


def test_pitch_import_does_not_require_jpype():
    """Importing the module must not pull in JPype (lazy dependency)."""
    import importlib
    mod = importlib.import_module("pyjevsim.hla.backends.pitch")
    assert hasattr(mod, "PitchTransport")


@requires_jvm
def test_encoder_round_trip():
    """The 1516e field codec round-trips int/string via the EncoderFactory."""
    import jpype
    from pyjevsim.hla.backends.pitch import _decode_field, _encode_field

    factory = jpype.JClass("hla.rti1516e.RtiFactoryFactory").getRtiFactory()
    ef = factory.getEncoderFactory()
    assert _decode_field(ef, "int32", _encode_field(ef, "int32", 42)) == 42
    assert _decode_field(ef, "string", _encode_field(ef, "string", "ping")) == "ping"


@requires_live
def test_live_pingpong_join_interaction_object():
    """End-to-end against a real CRC: join, rally, object sync, resign.

    Two time-managed federates run in their own threads (each is both
    regulating and constrained); the RTI coordinates time-advance grants
    and TSO delivery. Mirrors examples/hla_pingpong/run_pitch.py.
    """
    import threading

    from pingpong_models import (
        PINGPONG_FOM_MAP, Ping, Pong, ping_bindings, pong_bindings,
    )

    from pyjevsim import ExecutionType, SysExecutor
    from pyjevsim.hla import Federate, HLAExecutorFactory, create_rti

    def build(model, bindings, name):
        se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
        tx = create_rti("pitch", federation="PingPong", federate=name,
                        fom=FOM, fom_map=PINGPONG_FOM_MAP,
                        jvm_path=JVM, classpath=[JAR], lookahead=1.0)
        se.exec_factory = HLAExecutorFactory(tx, {name: bindings})
        se.register_entity(model)
        se.init_sim()
        return se, Federate(se, tx)

    ping_se, ping_fed = build(Ping("ping", max_volleys=3), ping_bindings(), "ping")
    pong_se, pong_fed = build(Pong("pong"), pong_bindings(), "pong")
    for fed, name, binds in ((ping_fed, "ping", ping_bindings()),
                             (pong_fed, "pong", pong_bindings())):
        fed.join("PingPong", name, fom_paths=[FOM])
        for b in binds.values():
            if b.direction in ("out", "inout"):
                fed.publish(b)
            if b.direction in ("in", "inout"):
                fed.subscribe(b)

    t_ping = threading.Thread(target=ping_fed.run_until, args=(25.0, 1.0))
    t_pong = threading.Thread(target=pong_fed.run_until, args=(25.0, 1.0))
    t_ping.start(); t_pong.start()
    t_ping.join(); t_pong.join()

    ping = ping_se.get_entity("ping")[0].get_core_model()
    pong = pong_se.get_entity("pong")[0].get_core_model()

    ping_counts = [d["count"] for d in pong.received_pings]   # 3. interaction
    pong_counts = [d["count"] for d in ping.received_pongs]
    assert ping_counts == list(range(len(ping_counts))) and len(ping_counts) >= 3
    assert pong_counts == list(range(len(pong_counts))) and len(pong_counts) >= 3
    assert pong.reflected_hits == ping_counts                 # 4. object sync

    ping_fed.resign()                                          # 2. resign
    pong_fed.resign()
