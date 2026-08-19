"""Equivalence gate against a *live* IEEE 1516-2010 RTI (Pitch / Portico).

Same criterion as verify_equivalence.py: the sorted, formatted trajectory rows
(tick, object, x, y, z) produced by the two-federate HLA build must exactly
equal the canonical reference file. Raw file bytes, wire data, and RTI
callback order are outside this criterion.

Each scenario runs in its own subprocess because JPype can start (and never
restart) exactly one JVM per process.

Env:
  PYJEVSIM_RTI   backend name: pitch | portico   (default: portico)
  PYJEVSIM_JAR   path to the RTI jar
  PYJEVSIM_JVM   path to jvm.dll / libjvm.so
  RTI_HOME       RTI distribution root (Portico)
  PYJEVSIM_LIVE_TIMEOUT  per-scenario process limit in seconds (default: 180)

Run:  python examples/hla_atsim/verify_equivalence_rti.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)

RTI = os.environ.get("PYJEVSIM_RTI", "portico")
LIVE_TIMEOUT = float(os.environ.get("PYJEVSIM_LIVE_TIMEOUT", "180"))
SCENARIO_TAGS = ("self_propelled", "stationary")   # self_propelled = regression guard
EXPECTED_DIR = Path(HERE).parents[1] / "docs" / "hla-validation" / "results"


def _expected_rows(tag: str):
    path = EXPECTED_DIR / f"expected_{tag}.csv"
    with path.open(encoding="utf-8") as stream:
        lines = [line.rstrip("\n") for line in stream]
    if not lines or lines[0] != "tick,object_name,x,y,z":
        raise ValueError(f"unexpected canonical trace header in {path}")
    return [tuple(line.split(",")) for line in lines[1:]]


def _rti_rows(tag: str):
    """Drive one live-RTI scenario in a subprocess; return its CSV rows."""
    out = os.path.join(HERE, f"hla_{RTI}_{tag}.csv")
    if os.path.exists(out):
        os.remove(out)
    env = dict(os.environ, PYJEVSIM_RTI=RTI)
    runner = "run_hla_portico.py" if RTI == "portico" else "run_hla_pitch.py"
    try:
        proc = subprocess.run(
            [sys.executable, os.path.join(HERE, runner), tag],
            env=env,
            cwd=HERE,
            capture_output=True,
            text=True,
            timeout=LIVE_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        print(
            f"[error] {RTI} process timed out for {tag} after "
            f"{LIVE_TIMEOUT:g}s"
        )
        if exc.stdout:
            print(str(exc.stdout)[-2000:])
        if exc.stderr:
            print(str(exc.stderr)[-2000:])
        return None
    if proc.returncode != 0:
        print(f"[error] {RTI} process failed for {tag}: rc={proc.returncode}")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        return None
    if not os.path.exists(out):
        print(f"[skip] {RTI} run produced no trace for {tag}")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        return None
    with open(out, encoding="utf-8") as stream:
        lines = [line.rstrip("\n") for line in stream]
    if not lines or lines[0] != "tick,object_name,x,y,z":
        print(f"[error] unexpected trace header in {out}")
        return None
    return [tuple(line.split(",")) for line in lines[1:]]


def check(tag: str) -> "bool | None":
    ref = _expected_rows(tag)
    got = _rti_rows(tag)
    if got is None:
        return None
    if len(ref) != len(got):
        print(
            f"MISMATCH {tag}: row counts reference={len(ref)} "
            f"{RTI}={len(got)}"
        )
        return False
    for i, (ra, rb) in enumerate(zip(ref, got)):
        if ra != rb:
            print(f"FIRST DIVERGENCE {tag} at row {i}:"
                  f"\n  reference={ra}\n  {RTI}={rb}")
            return False
    print(f"MATCH {tag}: {len(ref)} canonical rows ({RTI} vs reference)")
    return True


def main() -> None:
    results = [check(tag) for tag in SCENARIO_TAGS]
    if any(r is None for r in results):
        print("ERROR: live RTI validation did not produce every required trace")
        sys.exit(2)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
