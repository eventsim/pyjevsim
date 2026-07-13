"""Equivalence gate: standalone vs HLA-inprocess trajectories must match.

Runs both builds and asserts identical trajectory CSVs (tick,object,x,y,z),
printing a per-row first-divergence on mismatch and "MATCH: <n> rows" on
success. Exits non-zero on any mismatch so CI can gate on it.

Run:  python examples/hla_atsim/verify_equivalence.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from run_standalone_headless import run as run_standalone, resolve_scenario, SCENARIOS  # noqa: E402
from run_hla_inprocess import run as run_hla  # noqa: E402


def check(tag, path):
    a = sorted(run_standalone(path))
    b = sorted(run_hla(path))
    if len(a) != len(b):
        print(f"MISMATCH {tag}: row counts {len(a)} vs {len(b)}")
        for i, (ra, rb) in enumerate(zip(a, b)):
            if ra != rb:
                print(f"FIRST DIVERGENCE {tag} at row {i}:\n  standalone={ra}\n  hla={rb}")
                break
        return False
    for i, (ra, rb) in enumerate(zip(a, b)):
        if ra != rb:
            print(f"FIRST DIVERGENCE {tag} at row {i}:\n  standalone={ra}\n  hla={rb}")
            return False
    print(f"MATCH {tag}: {len(a)} rows")
    return True


def main():
    ok = True
    for tag in ("self_propelled", "stationary"):   # self_propelled first = regression guard
        if not check(tag, SCENARIOS[tag]):
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
