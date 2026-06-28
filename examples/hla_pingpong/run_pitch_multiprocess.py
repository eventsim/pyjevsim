"""Launch the two-process Pitch ping-pong demo from one command.

Spawns ``run_pitch_federate.py pong`` and ``run_pitch_federate.py ping`` as
two separate OS processes (each with its own JVM/LRC) joined to the same
live Pitch pRTI federation, and streams their output. Requires a running
CRC and ``PYJEVSIM_JVM`` set to a Java >= 9 ``jvm.dll``.

    python examples/hla_pingpong/run_pitch_multiprocess.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

HERE = os.path.dirname(__file__)
FEDERATE = os.path.join(HERE, "run_pitch_federate.py")


def _pump(proc, prefix):
    for line in proc.stdout:
        sys.stdout.write(f"{prefix} {line}")
        sys.stdout.flush()


def main() -> int:
    env = dict(os.environ)

    def spawn(role):
        return subprocess.Popen(
            [sys.executable, FEDERATE, role],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=env,
        )

    # Start pong (the subscriber) first and wait until it has joined and
    # subscribed before launching ping. ping then registers the start
    # synchronization point with both federates already joined, so the
    # RTI announces it to both (a point registered before a federate joins
    # is not announced to that late joiner).
    pong = spawn("pong")
    for line in pong.stdout:
        sys.stdout.write(f"pong| {line}")
        sys.stdout.flush()
        if "joined + published/subscribed" in line:
            break

    ping = spawn("ping")
    threads = [
        threading.Thread(target=_pump, args=(pong, "pong|")),
        threading.Thread(target=_pump, args=(ping, "ping|")),
    ]
    for t in threads:
        t.start()
    pong.wait(); ping.wait()
    for t in threads:
        t.join()

    print(f"\nexit codes: pong={pong.returncode} ping={ping.returncode}")
    return pong.returncode or ping.returncode


if __name__ == "__main__":
    raise SystemExit(main())
