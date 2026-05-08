"""Self-contained two-federate chat demo using LoopbackTransport.

Runs in a single process, no external RTI binaries needed. Best place
to start if you want to see pyjevsim.hla in action without standing
up Pitch or gorti.

Usage (from the pyjevsim repo root):

    python -m examples.hla.chat_loopback
    python -m examples.hla.chat_loopback --count 3 --period 0.5

What it demonstrates:
- One LoopbackTransport shared by both federates.
- Same Chatter BehaviorModel class (pure DEVS) registered twice with
  different names. No HLA awareness in the model.
- HLAExecutorFactory with bindings for both models. The factory builds
  one shared _HLARouter; each model's HLAExecutor subscribes through it.
- Driving the simulation with `sys_exec.step(t)` directly — Federate
  isn't needed since LoopbackTransport has no lifecycle to coordinate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python -m examples.hla.chat_loopback` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyjevsim import ExecutionType, SysExecutor
from pyjevsim.hla import (
    HLAExecutorFactory,
    HLAInteraction,
    LoopbackTransport,
)

from examples.hla._chat_model import Chatter

CHAT_CLASS = "HLAinteractionRoot.Communication"


def _bindings() -> dict:
    return {
        Chatter.OUTBOX: HLAInteraction(CHAT_CLASS, direction="out"),
        Chatter.INBOX: HLAInteraction(CHAT_CLASS, direction="in"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--count", type=int, default=3,
                   help="messages each federate sends (default 3)")
    p.add_argument("--period", type=float, default=1.0,
                   help="simulated seconds between sends (default 1.0)")
    p.add_argument("--end", type=float, default=10.0,
                   help="simulated end time (default 10.0)")
    args = p.parse_args()

    transport = LoopbackTransport()
    sys_exec = SysExecutor(_time_resolution=1, _sim_name="chat-demo",
                           ex_mode=ExecutionType.HLA_TIME)
    sys_exec.exec_factory = HLAExecutorFactory(
        transport=transport,
        bindings_by_model={"alice": _bindings(), "bob": _bindings()},
    )
    sys_exec.register_entity(
        Chatter("alice", period=args.period, message_count=args.count)
    )
    sys_exec.register_entity(
        Chatter("bob", period=args.period, message_count=args.count)
    )

    print(f"-- chat_loopback: each federate sends {args.count}, period={args.period}s --")
    t = 0.0
    while t < args.end:
        t += args.period
        sys_exec.step(t)

    transport.close()
    print(f"-- done at t={sys_exec.global_time} --")


if __name__ == "__main__":
    main()
