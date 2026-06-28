"""Ping-pong over two federates — RTI-agnostic logic verification.

Runs the *example* models (examples/hla_pingpong) as two separate
SysExecutor federates joined to one in-process federation, covering the four
deliverables without needing Java / pRTI:

  1. federates named ping / pong
  2. federation join / resign
  3. interaction send (the rally, both directions)
  4. object attribute synchronization (Ping.hits reflected by Pong)

The same models run against real Pitch pRTI via the ``pitch`` backend
(see tests/hla/test_pitch_backend.py, skipped when the toolchain is absent).
"""

from __future__ import annotations

import os
import sys

import pytest

# Import the example models (the authoritative ping-pong implementation).
_EXAMPLE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "examples", "hla_pingpong")
)
sys.path.insert(0, _EXAMPLE_DIR)
from pingpong_models import (  # noqa: E402
    Ping,
    Pong,
    ping_bindings,
    pong_bindings,
)

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402
from pyjevsim.hla import (  # noqa: E402
    Federate,
    HLAExecutorFactory,
    InProcessFederation,
    InProcessRTI,
)


def _build(model, bindings, model_name, federation):
    se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
    tx = InProcessRTI(federation=federation)
    se.exec_factory = HLAExecutorFactory(tx, {model_name: bindings})
    se.register_entity(model)
    se.init_sim()
    return se, tx, Federate(se, tx)


@pytest.fixture
def pingpong():
    """A joined ping + pong pair on a shared federation, pre-run 8 rounds."""
    federation = InProcessFederation("PingPong")
    ping_se, ping_tx, ping_fed = _build(Ping("ping", max_volleys=3),
                                        ping_bindings(), "ping", federation)
    pong_se, pong_tx, pong_fed = _build(Pong("pong"),
                                        pong_bindings(), "pong", federation)
    return {
        "federation": federation,
        "ping_se": ping_se, "ping_tx": ping_tx, "ping_fed": ping_fed,
        "pong_se": pong_se, "pong_tx": pong_tx, "pong_fed": pong_fed,
    }


def _join_all(ctx):
    for fed, name, binds in (
        (ctx["ping_fed"], "ping", ping_bindings()),
        (ctx["pong_fed"], "pong", pong_bindings()),
    ):
        fed.join("PingPong", name, fom_paths=["PingPong.xml"])
        for b in binds.values():
            if b.direction in ("out", "inout"):
                fed.publish(b)
            if b.direction in ("in", "inout"):
                fed.subscribe(b)


def _run(ctx, rounds=8):
    for t in range(1, rounds + 1):
        ctx["ping_se"].step(t)
        ctx["pong_se"].step(t)


# ----------------------------------------------------- 2. join / resign


def test_join_attaches_both_federates(pingpong):
    assert len(pingpong["federation"].members) == 0
    _join_all(pingpong)
    assert pingpong["ping_tx"].joined and pingpong["pong_tx"].joined
    assert len(pingpong["federation"].members) == 2


def test_publish_before_join_raises(pingpong):
    from pyjevsim.hla import HLAInteraction
    with pytest.raises(RuntimeError):
        pingpong["ping_fed"].publish(HLAInteraction("PingPong.Ping", direction="out"))


def test_resign_detaches_both_federates(pingpong):
    _join_all(pingpong)
    pingpong["ping_fed"].resign()
    pingpong["pong_fed"].resign()
    assert not pingpong["ping_tx"].joined and not pingpong["pong_tx"].joined
    assert len(pingpong["federation"].members) == 0


# ----------------------------------------------------- 3. interaction send


def test_interaction_rally_both_directions(pingpong):
    _join_all(pingpong)
    _run(pingpong, rounds=8)

    ping = pingpong["ping_se"].get_entity("ping")[0].get_core_model()
    pong = pingpong["pong_se"].get_entity("pong")[0].get_core_model()

    # Ping served (0) then returned 1,2,3 → Pong saw 0..3; Pong returned
    # each → Ping saw 0..3. Exactly max_volleys+1 balls each way.
    assert [d["count"] for d in pong.received_pings] == [0, 1, 2, 3]
    assert [d["count"] for d in ping.received_pongs] == [0, 1, 2, 3]
    # sender field carried across the interaction.
    assert all(d["sender"] == "ping" for d in pong.received_pings)
    assert all(d["sender"] == "pong" for d in ping.received_pongs)


# ----------------------------------------------------- 4. object sync


def test_object_attribute_synchronization(pingpong):
    _join_all(pingpong)
    _run(pingpong, rounds=8)

    ping = pingpong["ping_se"].get_entity("ping")[0].get_core_model()
    pong = pingpong["pong_se"].get_entity("pong")[0].get_core_model()

    # Pong reflected the hits attribute Ping published on every volley.
    assert pong.reflected_hits == [0, 1, 2, 3]
    # The reflected values track Ping's own ball counter.
    assert pong.reflected_hits[-1] == ping.count - 1 or pong.reflected_hits[-1] == ping.count


# ----------------------------------------------------- isolation


def test_separate_federations_do_not_cross_talk():
    """Two federations on separate buses must not exchange events."""
    fed_a = InProcessFederation("A")
    fed_b = InProcessFederation("B")
    a_se, a_tx, a_fed = _build(Ping("ping", max_volleys=3), ping_bindings(), "ping", fed_a)
    b_se, b_tx, b_fed = _build(Pong("pong"), pong_bindings(), "pong", fed_b)
    a_fed.join("A", "ping", fom_paths=["x"])
    b_fed.join("B", "pong", fom_paths=["x"])
    for t in range(1, 6):
        a_se.step(t)
        b_se.step(t)
    pong = b_se.get_entity("pong")[0].get_core_model()
    assert pong.received_pings == [], "different federations must be isolated"
