"""OPTIONAL live Portico (open-source IEEE 1516-2010 RTI) run of the
two-federate anti-torpedo sim.

Identical models, FOM, tick discipline and driver as run_hla_pitch.py -- only
the backend name and the RTI jar change. Portico needs no CRC process. Writes
``hla_portico_<scenario>.csv``, whose canonical rows are compared with the
repository reference file by verify_equivalence_rti.py.

Env:
  PYJEVSIM_JVM   path to jvm.dll / libjvm.so (default: Adoptium JDK 11)
  PYJEVSIM_JAR   path to portico.jar         (default: $RTI_HOME/lib/portico.jar)
  RTI_HOME       Portico distribution root
  RTI_RID_FILE   Portico configuration. By default this same-process example
                 uses the repository's ``portico-jvm.rid``. Set a custom RID
                 for multi-process or multi-host execution.

Run:  python examples/hla_atsim/run_hla_portico.py [scenario]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RTI_HOME = os.environ.get("RTI_HOME", "")
DEFAULT_RID = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "hla-validation"
    / "config"
    / "portico-jvm.rid"
)
os.environ.setdefault(
    "PYJEVSIM_JAR", os.path.join(RTI_HOME, "lib", "portico.jar")
)
os.environ.setdefault("RTI_RID_FILE", str(DEFAULT_RID))

import run_hla_pitch  # noqa: E402  (reads PYJEVSIM_JAR at import time)

run = run_hla_pitch.run


def main() -> None:
    run_hla_pitch.main(backend="portico")


if __name__ == "__main__":
    main()
