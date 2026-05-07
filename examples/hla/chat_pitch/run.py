"""Run a single chat federate against a Pitch RTI via kdx-rti gateway.

Prerequisites (see chat_pitch/README.md):
- Pitch pRTI running on its CRC port
- A kdx-rti gateway process bound to the ZMQ ports below
- pyjevsim, pyzmq, kdx-rti installed in this Python env

Usage:
    python -m examples.hla.chat_pitch.run alice
    python -m examples.hla.chat_pitch.run bob   --ports 5558,5559,5560

For a two-federate chat demo, run alice and bob in two terminals
against two gateway processes (one per federate seat).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running this file directly without installing the example dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla import Federate, HLAExecutorFactory, HLAInteraction

from examples.hla._chat_model import Chatter
from examples.hla.chat_pitch.transport import PitchTransport

try:
    from kdx_rti.transport import GatewayEndpoints
except ImportError as e:
    raise SystemExit(
        "kdx-rti is not installed. From the kdx-rti repo: "
        "`pip install -e python/`"
    ) from e


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("name", help="federate name, e.g. alice or bob")
    p.add_argument("--ports", default="5555,5556,5557",
                   help="ctrl,data_out,data_in ports for the gateway")
    p.add_argument("--end", type=float, default=10.0,
                   help="run-until simulated time")
    p.add_argument("--lookahead", type=float, default=0.1)
    p.add_argument("--period", type=float, default=1.0)
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--log", default="INFO")
    args = p.parse_args()

    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO),
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    ctrl, dout, din = (int(x) for x in args.ports.split(","))
    endpoints = GatewayEndpoints(
        control=f"tcp://localhost:{ctrl}",
        data_out=f"tcp://localhost:{dout}",
        data_in=f"tcp://localhost:{din}",
    )

    transport = PitchTransport(endpoints=endpoints)
    sys_exec = SysExecutor(_time_resolution=1, _sim_name=f"{args.name}-sim",
                           ex_mode=ExecutionType.HLA_TIME)

    chat_class = "HLAinteractionRoot.Communication"
    bindings = {
        Chatter.OUTBOX: HLAInteraction(chat_class, direction="out"),
        Chatter.INBOX: HLAInteraction(chat_class, direction="in"),
    }
    sys_exec.exec_factory = HLAExecutorFactory(
        transport=transport,
        bindings_by_model={args.name: bindings},
    )
    sys_exec.register_entity(Chatter(args.name, period=args.period,
                                     message_count=args.count))

    fed = Federate(sys_exec, transport)
    fed.join("ChatFederation", args.name, fom_paths=["Chat-evolved.xml"])
    fed.publish(bindings[Chatter.OUTBOX])
    fed.subscribe(bindings[Chatter.INBOX])

    try:
        fed.run_until(end_time=args.end, lookahead=args.lookahead)
    finally:
        fed.resign()
        transport.close()


if __name__ == "__main__":
    main()
