"""One ping-pong federate per OS process — a true multi-process HLA demo.

Run each federate in its own process (own JVM, own LRC), joined to the same
Pitch pRTI federation. The RTI mediates all data exchange and time
management, so the two federates are genuinely distributed (and may be on
different hosts — point each at the CRC with ``PYJEVSIM_CRC``).

Two terminals:

    # terminal 1
    set PYJEVSIM_JVM=C:\\Program Files\\Eclipse Adoptium\\jdk-11...\\bin\\server\\jvm.dll
    python examples/hla_pingpong/run_pitch_federate.py pong

    # terminal 2 (start within a few seconds; a sync point makes order safe)
    python examples/hla_pingpong/run_pitch_federate.py ping

Both federates register/await a ``ready`` synchronization point before any
data flows, so neither serves until both have joined and subscribed.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from pingpong_models import (  # noqa: E402
    PINGPONG_FOM_MAP,
    Ping,
    Pong,
    ping_bindings,
    pong_bindings,
)

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402
from pyjevsim.hla import Federate, HLAExecutorFactory, create_rti  # noqa: E402

PRTI_HOME = os.environ.get("PRTI_HOME", r"C:\Program Files\prti1516e")
JAR = os.path.join(PRTI_HOME, "lib", "prti1516e.jar")
FOM = os.path.join(os.path.dirname(__file__), "fom", "PingPong.xml")
JVM_PATH = os.environ.get("PYJEVSIM_JVM")          # Java >= 9 jvm.dll
CRC = os.environ.get("PYJEVSIM_CRC")               # e.g. 192.168.1.10:8989
SYNC = "ready"


def build_role(role: str, max_volleys: int):
    if role == "ping":
        model, bindings = Ping("ping", max_volleys=max_volleys), ping_bindings()
    elif role == "pong":
        model, bindings = Pong("pong"), pong_bindings()
    else:
        raise SystemExit(f"role must be 'ping' or 'pong', got {role!r}")
    se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
    tx = create_rti(
        "pitch",
        federation="PingPong", federate=role,
        fom=FOM, fom_map=PINGPONG_FOM_MAP,
        jvm_path=JVM_PATH, classpath=[JAR], lookahead=1.0, crc=CRC,
    )
    se.exec_factory = HLAExecutorFactory(tx, {role: bindings})
    se.register_entity(model)
    se.init_sim()
    return se, tx, Federate(se, tx), bindings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["ping", "pong"])
    ap.add_argument("--end-time", type=float, default=25.0)
    ap.add_argument("--lookahead", type=float, default=1.0)
    ap.add_argument("--max-volleys", type=int, default=3)
    args = ap.parse_args()

    se, tx, fed, bindings = build_role(args.role, args.max_volleys)

    fed.join("PingPong", args.role, fom_paths=[FOM])
    for b in bindings.values():
        if b.direction in ("out", "inout"):
            fed.publish(b)
        if b.direction in ("in", "inout"):
            fed.subscribe(b)
    print(f"[{args.role}] joined + published/subscribed", flush=True)

    # Start barrier: ping registers the sync point, both achieve it once
    # announced, and both wait until the whole federation is synchronized
    # before any event is exchanged. This removes the join/subscribe race.
    # (Start pong before ping so the point is registered after both joined.)
    if args.role == "ping":
        tx.register_sync_point(SYNC)
    if not tx.wait_sync_announced(SYNC):
        raise SystemExit(f"[{args.role}] sync point '{SYNC}' not announced (timeout)")
    tx.achieve_sync_point(SYNC)
    if not tx.wait_synchronized(SYNC):
        raise SystemExit(f"[{args.role}] federation not synchronized (timeout)")
    print(f"[{args.role}] federation synchronized - starting", flush=True)

    fed.run_until(end_time=args.end_time, lookahead=args.lookahead)

    model = se.get_entity(args.role)[0].get_core_model()
    if args.role == "pong":
        print(f"[pong] received pings: {[d['count'] for d in model.received_pings]}", flush=True)
        print(f"[pong] reflected hits: {model.reflected_hits}", flush=True)
    else:
        print(f"[ping] received pongs: {[d['count'] for d in model.received_pongs]}", flush=True)

    fed.resign()
    tx.close()
    print(f"[{args.role}] resigned", flush=True)


if __name__ == "__main__":
    main()
