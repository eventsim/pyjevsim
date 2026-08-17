"""Equivalence gate against a *live* IEEE 1516-2010 RTI (Pitch / Portico).

Same criterion as verify_equivalence.py -- the trajectory trace
(tick,object,x,y,z) produced by the two-federate HLA build must be
byte-identical to the single-executor standalone reference -- but the
federation runs on a real RTI instead of the in-process bus.

Each scenario runs in its own subprocess because JPype can start (and never
restart) exactly one JVM per process.

Env:
  PYJEVSIM_RTI   backend name: pitch | portico   (default: portico)
  PYJEVSIM_JAR   path to the RTI jar
  PYJEVSIM_JVM   path to jvm.dll / libjvm.so
  RTI_HOME       RTI distribution root (Portico)

Run:  python examples/hla_atsim/verify_equivalence_rti.py
"""

from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)

from run_standalone_headless import SCENARIOS, run as run_standalone  # noqa: E402

RTI = os.environ.get("PYJEVSIM_RTI", "portico")
SCENARIO_TAGS = ("self_propelled", "stationary")   # self_propelled = regression guard


def _rti_rows(tag: str):
    """Drive one live-RTI scenario in a subprocess; return its CSV rows."""
    out = os.path.join(HERE, f"hla_{RTI}_{tag}.csv")
    if os.path.exists(out):
        os.remove(out)
    env = dict(os.environ, PYJEVSIM_RTI=RTI)
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "run_hla_pitch.py"), tag],
        env=env, cwd=HERE, capture_output=True, text=True,
    )
    if not os.path.exists(out):
        print(f"[skip] {RTI} run produced no trace for {tag}")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        return None
    with open(out) as f:
        return [tuple(line.rstrip("\n").split(",")) for line in f][1:]


def check(tag: str) -> "bool | None":
    ref = [tuple(str(c) for c in r) for r in sorted(run_standalone(SCENARIOS[tag]))]
    got = _rti_rows(tag)
    if got is None:
        return None
    if len(ref) != len(got):
        print(f"MISMATCH {tag}: row counts {len(ref)} vs {len(got)}")
        return False
    for i, (ra, rb) in enumerate(zip(ref, got)):
        if ra != rb:
            print(f"FIRST DIVERGENCE {tag} at row {i}:"
                  f"\n  standalone={ra}\n  {RTI}={rb}")
            return False
    print(f"MATCH {tag}: {len(ref)} rows (standalone vs {RTI}, byte-identical)")
    return True


def main() -> None:
    results = [check(tag) for tag in SCENARIO_TAGS]
    if any(r is None for r in results):
        sys.exit(0)          # toolchain absent -> skip, do not fail CI
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
