"""Run a single chat federate against gorti rtid.

Prerequisites (see chat_gorti/README.md):
- gorti rtid running (or use the `memory://...` in-process URL)
- pyjevsim, gorti pysdk installed

Usage:
    python -m examples.hla.chat_gorti.run alice --url grpc://localhost:7000
    python -m examples.hla.chat_gorti.run bob   --url grpc://localhost:7000

For a quick smoke test against an in-process fake RTI, use
`--url memory://chat-rti` for both federates. Run them in separate
processes — they share the in-memory RTI by URL.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla import Federate, HLAExecutorFactory, HLAInteraction

from examples.hla._chat_model import Chatter
from examples.hla._trace import TracingTransport
from examples.hla.chat_gorti.transport import GortiTransport


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("name", help="federate name, e.g. alice or bob")
    p.add_argument("--url", default="memory://chat-rti",
                   help="gorti RTI URL (memory://, grpc://, ...)")
    p.add_argument("--end", type=float, default=10.0,
                   help="run-until simulated time")
    p.add_argument("--lookahead", type=float, default=0.1)
    p.add_argument("--period", type=float, default=1.0)
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--log", default="INFO")
    p.add_argument("--trace-file",
                   help="write canonical event-sequence trace to this file "
                        "(for cross-RTI semantics comparison vs chat_pitch)")
    args = p.parse_args()

    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO),
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    transport = GortiTransport(url=args.url)
    if args.trace_file:
        trace_sink = open(args.trace_file, "w", buffering=1)
        transport = TracingTransport(transport, sink=trace_sink)

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
    fed.join("ChatFederation", args.name, fom_paths=["chat.fom.xml"])
    fed.publish(bindings[Chatter.OUTBOX])
    fed.subscribe(bindings[Chatter.INBOX])

    try:
        fed.run_until(end_time=args.end, lookahead=args.lookahead)
    finally:
        fed.resign()
        transport.close()


if __name__ == "__main__":
    main()
