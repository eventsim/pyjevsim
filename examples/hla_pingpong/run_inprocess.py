"""Offline ping-pong demo — two federates over the in-process RTI bus.

No Java / pRTI required. Two separate SysExecutor federates (``ping`` and
``pong``) join one :class:`InProcessFederation` and rally a ball via HLA
interactions, while Ping's ``hits`` object attribute is reflected by Pong.

Run:  python examples/hla_pingpong/run_inprocess.py
"""

from __future__ import annotations

import os
import sys

# Prefer the dev source tree over any installed pyjevsim wheel.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from pingpong_models import Ping, Pong, ping_bindings, pong_bindings  # noqa: E402

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402
from pyjevsim.hla import (  # noqa: E402
    Federate,
    HLAExecutorFactory,
    InProcessFederation,
    InProcessRTI,
)

FOM = os.path.join(os.path.dirname(__file__), "fom", "PingPong.xml")


def build_federate(model, bindings, model_name, federation):
    se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
    transport = InProcessRTI(federation=federation)
    se.exec_factory = HLAExecutorFactory(transport, {model_name: bindings})
    se.register_entity(model)
    se.init_sim()
    fed = Federate(se, transport)
    return se, transport, fed


def main(max_volleys: int = 3, rounds: int = 8) -> None:
    federation = InProcessFederation("PingPong")

    ping_se, ping_tx, ping_fed = build_federate(
        Ping("ping", max_volleys=max_volleys), ping_bindings(), "ping", federation
    )
    pong_se, pong_tx, pong_fed = build_federate(
        Pong("pong"), pong_bindings(), "pong", federation
    )

    # join + publish/subscribe each federate
    for fed, name, binds in (
        (ping_fed, "ping", ping_bindings()),
        (pong_fed, "pong", pong_bindings()),
    ):
        fed.join("PingPong", name, fom_paths=[FOM])
        for b in binds.values():
            if b.direction in ("out", "inout"):
                fed.publish(b)
            if b.direction in ("in", "inout"):
                fed.subscribe(b)

    print(f"federation members after join: {len(federation.members)}")

    # Coordinated lock-step advance (the in-process bus does no time mgmt).
    for t in range(1, rounds + 1):
        ping_se.step(t)
        pong_se.step(t)

    ping = ping_se.get_entity("ping")[0].get_core_model()
    pong = pong_se.get_entity("pong")[0].get_core_model()
    print("pong received pings:", [d["count"] for d in pong.received_pings])
    print("ping received pongs:", [d["count"] for d in ping.received_pongs])
    print("pong reflected hits (object sync):", pong.reflected_hits)

    ping_fed.resign()
    pong_fed.resign()
    print(f"federation members after resign: {len(federation.members)}")


if __name__ == "__main__":
    main()
