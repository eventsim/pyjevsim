"""Equivalence gate for the committed canonical AT/SIM trajectories.

Runs the standalone and HLA-inprocess builds and requires both to equal the
committed canonical rows (tick, object, x, y, z).  It prints the first
divergence on mismatch and exits non-zero so CI can gate on it.

Run:  python examples/hla_atsim/verify_equivalence.py
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from run_standalone_headless import run as run_standalone, SCENARIOS  # noqa: E402
from run_hla_inprocess import run as run_hla  # noqa: E402

HERE = Path(__file__).resolve().parent
EXPECTED_DIR = HERE.parents[1] / "docs" / "hla-validation" / "results"
EXPECTED_HEADER = ["tick", "object_name", "x", "y", "z"]


def load_expected(tag: str):
    """Load the committed canonical trajectory."""
    path = EXPECTED_DIR / f"expected_{tag}.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if header != EXPECTED_HEADER:
            raise ValueError(f"unexpected header in {path}: {header!r}")
        return [
            (int(tick), object_name, x, y, z)
            for tick, object_name, x, y, z in reader
        ]


def _compare(tag, actual_name, actual, expected):
    if len(actual) != len(expected):
        print(
            f"MISMATCH {tag} ({actual_name} vs committed reference): "
            f"row counts {len(actual)} vs {len(expected)}"
        )
        return False
    for i, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            print(
                f"FIRST DIVERGENCE {tag} at row {i}:"
                f"\n  {actual_name}={got}\n  committed={want}"
            )
            return False
    return True


def check(tag, path):
    expected = load_expected(tag)
    standalone = sorted(run_standalone(path))
    hla = sorted(run_hla(path))
    standalone_ok = _compare(tag, "standalone", standalone, expected)
    hla_ok = _compare(tag, "hla-inprocess", hla, expected)
    ok = standalone_ok and hla_ok
    if ok:
        print(f"MATCH {tag}: {len(expected)} rows")
    return ok


def main():
    ok = True
    for tag in ("self_propelled", "stationary"):   # self_propelled first = regression guard
        if not check(tag, SCENARIOS[tag]):
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
