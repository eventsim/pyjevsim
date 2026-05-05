"""Sparse-time baseline runner.

Runs a tiny "Generator → Sink" topology against every available engine while
sweeping the inter-event period. The total work (count of transitions) is
held constant at `--count`; only the simulated-time gap between events
changes. This isolates the cost of the V_TIME tick-stepping loop.

Examples
--------

Default sweep:

    python -m benchmark.run_sparse

Single config:

    python -m benchmark.run_sparse --period 100 --count 100

Save CSV:

    python -m benchmark.run_sparse --output benchmark/results/sparse.csv
"""

import argparse
import csv
import os
import sys
import traceback

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.engines.common import RunResult  # noqa: E402
from benchmark.engines.pyjevsim import sparse as pyjevsim_sparse  # noqa: E402
from benchmark.engines.pypdevs import sparse as pypdevs_sparse  # noqa: E402
from benchmark.engines.reference import sparse as reference_sparse  # noqa: E402
from benchmark.engines.xdevs import sparse as xdevs_sparse  # noqa: E402


ENGINE_RUNNERS = {
    pyjevsim_sparse.ENGINE_NAME: pyjevsim_sparse,
    xdevs_sparse.ENGINE_NAME: xdevs_sparse,
    pypdevs_sparse.ENGINE_NAME: pypdevs_sparse,
    reference_sparse.ENGINE_NAME: reference_sparse,
}


DEFAULT_PERIODS = [1, 10, 100, 1000]
DEFAULT_COUNT = 100


def available_engines():
    return [n for n, m in ENGINE_RUNNERS.items() if m.is_available()]


def run_grid(periods, count, engines, repeat=3):
    results: list[RunResult] = []
    for period in periods:
        for engine_name in engines:
            mod = ENGINE_RUNNERS[engine_name]
            best: RunResult | None = None
            for _ in range(repeat):
                try:
                    res = mod.run_sparse(period, count)
                except Exception as exc:
                    res = RunResult(
                        engine=engine_name,
                        variant=f"sparse_p{int(period)}",
                        depth=1, width=1,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    traceback.print_exc(file=sys.stderr)
                if best is None or (res.error == "" and res.sim_s < best.sim_s):
                    best = res
            assert best is not None
            results.append(best)
    return results


def format_table(results):
    header = (
        f"{'engine':>10} {'period':>7} {'count':>6} {'events':>7} "
        f"{'sim_s':>10} {'tr/s':>11}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        if r.error:
            lines.append(f"{r.engine:>10}  {r.variant}  ERROR: {r.error}")
            continue
        period = r.variant.replace("sparse_p", "")
        lines.append(
            f"{r.engine:>10} {period:>7} {r.n_internals:>6} {r.n_events:>7} "
            f"{r.sim_s:>10.4f} {r.transitions_per_s:>11,.0f}"
        )
    return "\n".join(lines)


def write_csv(results, path):
    fields = list(results[0].as_dict().keys()) if results else []
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(r.as_dict())


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Sparse-time DEVS comparison")
    p.add_argument("--periods", nargs="+", type=int, default=None)
    p.add_argument("--period", type=int, default=None,
                   help="single period (overrides --periods)")
    p.add_argument("--count", type=int, default=DEFAULT_COUNT,
                   help="number of generator firings per run")
    p.add_argument("--engines", nargs="+", default=None)
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--output", default=None)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.engines:
        unknown = set(args.engines) - set(ENGINE_RUNNERS)
        if unknown:
            print(f"unknown engines: {unknown}", file=sys.stderr)
            return 2
        engines = [e for e in args.engines if ENGINE_RUNNERS[e].is_available()]
    else:
        engines = available_engines()

    if not engines:
        print("no engines available", file=sys.stderr)
        return 1

    if args.period is not None:
        periods = [args.period]
    elif args.periods:
        periods = args.periods
    else:
        periods = DEFAULT_PERIODS

    results = run_grid(periods, args.count, engines, args.repeat)
    print(format_table(results))

    if args.output:
        write_csv(results, args.output)
        print(f"\nwrote {len(results)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
