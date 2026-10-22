"""Cross-engine DEVStone comparison runner.

Runs the same DEVStone configurations against every engine adapter that is
available on the current system and tabulates wall-clock time, transition
counts, and transitions/sec. Use this to pin down the pyjevsim performance
baseline relative to xdevs and a hand-rolled reference engine.

Examples
--------

Run the default sweep against every available engine:

    python -m benchmark.run_compare

Run a single configuration:

    python -m benchmark.run_compare --variant HI --depth 4 --width 4

Restrict to specific engines:

    python -m benchmark.run_compare --engines pyjevsim xdevs

Persist results to CSV:

    python -m benchmark.run_compare --output benchmark/results/baseline.csv

Steady-state (multi-event) mode: inject N seed events into the same root
input at simulated times 0, P, 2P, ... instead of a single seed at t=0.
Every seed's zero-delay cascade drains before the next one arrives (P > 0),
so transitions(N) == N * transitions(1) for every engine. The seed
generator's own transitions are not counted:

    python -m benchmark.run_compare --variant HI --depth 10 --width 10 --events 100 --period 1.0

--events 1 (the default) runs exactly the historical single-event path.
"""

import argparse
import csv
import os
import sys
import traceback

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.engines.common import RunResult, VARIANTS, check_events  # noqa: E402
from benchmark.engines.pyjevsim import runner as pyjevsim_runner  # noqa: E402
from benchmark.engines.pypdevs import runner as pypdevs_runner  # noqa: E402
from benchmark.engines.reference import runner as reference_runner  # noqa: E402
from benchmark.engines.xdevs import runner as xdevs_runner  # noqa: E402


ENGINE_RUNNERS = {
    pyjevsim_runner.ENGINE_NAME: pyjevsim_runner,
    xdevs_runner.ENGINE_NAME: xdevs_runner,
    pypdevs_runner.ENGINE_NAME: pypdevs_runner,
    reference_runner.ENGINE_NAME: reference_runner,
}


DEFAULT_GRID = [
    ("LI", 2, 2),
    ("LI", 4, 4),
    ("LI", 6, 6),
    ("HI", 2, 2),
    ("HI", 4, 4),
    ("HI", 6, 6),
    ("HO", 2, 2),
    ("HO", 4, 4),
    ("HO", 6, 6),
]


def available_engines() -> list[str]:
    return [name for name, mod in ENGINE_RUNNERS.items() if mod.is_available()]


def run_grid(grid, engines, int_cycles=0, ext_cycles=0, repeat=1,
             events=1, period=1.0, xdevs_seed="auto"):
    results: list[RunResult] = []
    for variant, depth, width in grid:
        for engine_name in engines:
            mod = ENGINE_RUNNERS[engine_name]
            extra = {}
            if engine_name == "xdevs" and xdevs_seed != "auto":
                extra["seed"] = xdevs_seed
            best: RunResult | None = None
            for _ in range(repeat):
                try:
                    res = mod.run(variant, depth, width, int_cycles, ext_cycles,
                                  events=events, period=period, **extra)
                except Exception as exc:
                    res = RunResult(
                        engine=engine_name, variant=variant,
                        depth=depth, width=width,
                        int_cycles=int_cycles, ext_cycles=ext_cycles,
                        error=f"{type(exc).__name__}: {exc}",
                        events=events, period=period,
                    )
                    traceback.print_exc(file=sys.stderr)
                if best is None or (res.error == "" and res.sim_s < best.sim_s):
                    best = res
            assert best is not None
            results.append(best)
    return results


def format_table(results: list[RunResult]) -> str:
    # The events/period columns appear only in multi-event mode so the
    # single-event table is byte-identical to the historical output.
    multi = any(r.events != 1 for r in results)
    ev_head = f" {'events':>7} {'period':>7}" if multi else ""
    header = (
        f"{'engine':>10} {'variant':>7} {'d':>2} {'w':>2}{ev_head} "
        f"{'atomics':>8} {'transitions':>11} "
        f"{'sim_s':>9} {'tr/s':>11}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        ev = f" {r.events:>7} {r.period:>7g}" if multi else ""
        if r.error:
            lines.append(
                f"{r.engine:>10} {r.variant:>7} {r.depth:>2} {r.width:>2}{ev} "
                f"{'-':>8} {'-':>11} {'-':>9} {'-':>11}  ERROR: {r.error}"
            )
            continue
        lines.append(
            f"{r.engine:>10} {r.variant:>7} {r.depth:>2} {r.width:>2}{ev} "
            f"{r.n_atomics:>8} {r.transitions:>11} "
            f"{r.sim_s:>9.4f} {r.transitions_per_s:>11,.0f}"
        )
    return "\n".join(lines)


def write_csv(results: list[RunResult], path: str):
    fields = list(results[0].as_dict().keys()) if results else []
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(r.as_dict())


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Cross-engine DEVStone comparison")
    p.add_argument("--variant", choices=VARIANTS,
                   help="single-config variant; omit to use --sweep")
    p.add_argument("--depth", type=int, default=4)
    p.add_argument("--width", type=int, default=4)
    p.add_argument("--engines", nargs="+", default=None,
                   help="restrict to these engines (default: all available)")
    p.add_argument("--int-cycles", type=int, default=0,
                   help="dhrystone-style cycles per internal transition")
    p.add_argument("--ext-cycles", type=int, default=0,
                   help="dhrystone-style cycles per external transition")
    p.add_argument("--repeat", type=int, default=3,
                   help="run each config N times and keep the best")
    p.add_argument("--events", type=int, default=1,
                   help="number of seed events injected into the root input "
                        "at t = 0, P, 2P, ... (default 1: the historical "
                        "single-event cascade)")
    p.add_argument("--period", type=float, default=1.0,
                   help="simulated time P between seed events (default 1.0; "
                        "must be > 0)")
    p.add_argument("--xdevs-seed", choices=("auto", "generator"),
                   default="auto",
                   help="xdevs seeding: 'auto' keeps the historical "
                        "Coordinator.inject path for --events 1 and uses a "
                        "seed generator otherwise; 'generator' uses the "
                        "generator also for --events 1 (see "
                        "engines/xdevs/runner.py for why this matters for "
                        "HO and for sim_s)")
    p.add_argument("--output", default=None,
                   help="path to write CSV output to")
    p.add_argument("--list-engines", action="store_true",
                   help="print engine availability and exit")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        check_events(args.events, args.period)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.list_engines:
        for name, mod in ENGINE_RUNNERS.items():
            mark = "available" if mod.is_available() else "missing"
            print(f"  {name:<12} {mark}")
        return 0

    if args.engines:
        unknown = set(args.engines) - set(ENGINE_RUNNERS)
        if unknown:
            print(f"unknown engines: {unknown}", file=sys.stderr)
            return 2
        engines = [e for e in args.engines if ENGINE_RUNNERS[e].is_available()]
        missing = [e for e in args.engines if not ENGINE_RUNNERS[e].is_available()]
        for e in missing:
            print(f"engine '{e}' is not available; skipping", file=sys.stderr)
    else:
        engines = available_engines()

    if not engines:
        print("no engines available", file=sys.stderr)
        return 1

    if args.variant is None:
        grid = DEFAULT_GRID
    else:
        grid = [(args.variant, args.depth, args.width)]

    results = run_grid(
        grid, engines,
        int_cycles=args.int_cycles,
        ext_cycles=args.ext_cycles,
        repeat=args.repeat,
        events=args.events,
        period=args.period,
        xdevs_seed=args.xdevs_seed,
    )

    print(format_table(results))

    if args.output:
        write_csv(results, args.output)
        print(f"\nwrote {len(results)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
