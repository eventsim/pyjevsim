"""
DEVStone benchmark runner for pyjevsim.

Examples:
    # Single configuration
    python -m benchmark.run_devstone --variant li --depth 4 --width 4 --events 50

    # Quick parameter sweep, CSV to stdout
    python -m benchmark.run_devstone --sweep --csv

    # Persist a sweep into benchmark/results/
    python -m benchmark.run_devstone --sweep --csv \
        --output benchmark/results/devstone.csv
"""

import argparse
import csv
import io
import os
import sys
import time

# Allow running both as "python -m benchmark.run_devstone" and as a script.
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.devstone.topology import build_devstone


def run_one(variant, depth, width, events, period, dhrystones):
    ss, handles = build_devstone(
        variant=variant,
        depth=depth,
        width=width,
        gen_count=events,
        gen_period=period,
        dhrystones=dhrystones,
    )

    # Run long enough for every generator firing to drain through the graph.
    sim_horizon = events * period + depth + 2

    start = time.perf_counter()
    ss.simulate(sim_horizon, _tm=False)
    elapsed = time.perf_counter() - start

    ext_total, int_total = 0, 0
    for level in handles["levels"]:
        for atomic in level:
            e, i = atomic.get_counts()
            ext_total += e
            int_total += i

    return {
        "variant": variant,
        "depth": depth,
        "width": width,
        "events": events,
        "dhrystones": dhrystones,
        "sim_time_s": round(elapsed, 6),
        "transitions": ext_total + int_total,
        "ext_trans": ext_total,
        "int_trans": int_total,
        "sink_received": handles["sink"].get_received(),
        "events_per_s": round((ext_total + int_total) / elapsed, 2) if elapsed else 0,
    }


def format_row(result):
    return (
        f"{result['variant']:>3} d={result['depth']:>2} w={result['width']:>2} "
        f"events={result['events']:>4} | "
        f"transitions={result['transitions']:>7} "
        f"sink={result['sink_received']:>5} | "
        f"{result['sim_time_s']:>7.3f} s "
        f"({result['events_per_s']:>10.0f} ev/s)"
    )


def write_csv(results, fp):
    fields = [
        "variant", "depth", "width", "events", "dhrystones",
        "sim_time_s", "transitions", "ext_trans", "int_trans",
        "sink_received", "events_per_s",
    ]
    writer = csv.DictWriter(fp, fieldnames=fields)
    writer.writeheader()
    for r in results:
        writer.writerow(r)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="pyjevsim DEVStone benchmark")
    p.add_argument("--variant", choices=["li", "hi", "ho"], default="li")
    p.add_argument("--depth", type=int, default=3)
    p.add_argument("--width", type=int, default=3)
    p.add_argument("--events", type=int, default=20)
    p.add_argument("--period", type=float, default=1.0)
    p.add_argument("--dhrystones", type=int, default=0,
                   help="synthetic CPU work per ext_trans (0 = simulator overhead only)")
    p.add_argument("--sweep", action="store_true",
                   help="run all variants across a small parameter grid")
    p.add_argument("--csv", action="store_true",
                   help="emit CSV (to stdout, or to --output if given)")
    p.add_argument("--output", default=None,
                   help="path to write CSV output to")
    return p.parse_args(argv)


def sweep_grid():
    grid = []
    for variant in ("li", "hi", "ho"):
        for depth, width in ((2, 2), (3, 3), (4, 4), (5, 3)):
            grid.append((variant, depth, width, 20))
    return grid


def main(argv=None):
    args = parse_args(argv)

    if args.sweep:
        configs = sweep_grid()
    else:
        configs = [(args.variant, args.depth, args.width, args.events)]

    results = []
    for variant, depth, width, events in configs:
        res = run_one(variant, depth, width, events, args.period, args.dhrystones)
        results.append(res)
        print(format_row(res), file=sys.stderr if args.csv else sys.stdout, flush=True)

    if args.csv or args.output:
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
            with open(args.output, "w", newline="") as f:
                write_csv(results, f)
            print(f"wrote {len(results)} rows to {args.output}")
        else:
            buf = io.StringIO()
            write_csv(results, buf)
            sys.stdout.write(buf.getvalue())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
