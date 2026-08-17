"""Live ping-pong against the open-source Portico RTI (IEEE 1516-2010).

Same models, same driver and same FOM as run_pitch.py -- only the backend
name and the RTI jar change. Portico needs no CRC process: the first
federate to create the federation elects itself co-ordinator.

Prerequisites:
  * pip install jpype1   (matching your Python; JPype>=1.6 needs Java>=9)
  * a Portico distribution (https://github.com/openlvc/portico/releases)

Env:
  PYJEVSIM_JAR   path to portico.jar   (default: $RTI_HOME/lib/portico.jar)
  PYJEVSIM_JVM   path to jvm.dll / libjvm.so (optional but recommended)
  RTI_HOME       Portico distribution root

Run:  python examples/hla_pingpong/run_portico.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RTI_HOME = os.environ.get("RTI_HOME", "")
os.environ.setdefault(
    "PYJEVSIM_JAR", os.path.join(RTI_HOME, "lib", "portico.jar")
)

import run_pitch  # noqa: E402  (reads PYJEVSIM_JAR at import time)


def main() -> None:
    if not os.path.exists(run_pitch.JAR):
        print(f"[skip] portico.jar not found at {run_pitch.JAR} "
              f"(set PYJEVSIM_JAR or RTI_HOME)")
        return
    run_pitch.main(rti="portico")


if __name__ == "__main__":
    main()
