"""Standalone (single-executor) reference run of the anti-torpedo scenario.

Uses the 1-tick snapshot sensing convention (detectors read end-of-previous
-tick positions) so the trajectories are fully deterministic and match the
HLA in-process build exactly. Dumps a CSV: tick,object_name,x,y,z.

Run:  python examples/hla_atsim/run_standalone_headless.py
"""

from __future__ import annotations

import os
import sys

# Prefer the dev source tree over any installed pyjevsim wheel, and make
# model.* / mobject.* / utils.* resolve as top-level packages.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402

from utils.sim_context import SimContext  # noqa: E402
from utils.builder import load_scenario, build_ship, build_torpedo  # noqa: E402
from utils.ticking import commit_tick  # noqa: E402

SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "scenarios")
SCENARIOS = {
    "self_propelled": os.path.join(SCENARIO_DIR, "self_propelled_decoy.yaml"),
    "stationary":     os.path.join(SCENARIO_DIR, "stationary_decoy.yaml"),
}
DEFAULT_SCENARIO = "self_propelled"
SCENARIO = SCENARIOS[DEFAULT_SCENARIO]   # back-compat default (path); imported by the HLA runners
TICKS = 30


def resolve_scenario(selector=None):
    """Map a selector to (tag, path). None -> $PYJEVSIM_SCENARIO -> default;
    a registry key -> its path; otherwise treat selector as a yaml path.
    `tag` names the per-scenario CSV file."""
    if selector is None:
        selector = os.environ.get("PYJEVSIM_SCENARIO", DEFAULT_SCENARIO)
    if selector in SCENARIOS:
        return selector, SCENARIOS[selector]
    return os.path.splitext(os.path.basename(selector))[0], selector


def record(rows, t, items):
    for o in sorted(items, key=lambda o: o.sense_id):
        x, y, z = o.get_position()
        rows.append((t, o.sense_id, "%.10g" % x, "%.10g" % y, "%.10g" % z))


def run(scenario=SCENARIO):
    ctx = SimContext()
    se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
    ctx.set_executor(se)

    data = load_scenario(scenario)
    ship = build_ship("blue_ship_0", data["SurfaceShip"][0], ctx)
    torp = build_torpedo("red_torpedo_0", data["Torpedo"][0], ctx)

    se.insert_input_port("start")
    for m in (ship, torp):
        se.register_entity(m)
        se.coupling_relation(se, "start", m, "start")

    se.init_sim()
    se.insert_external_event("start", None)

    rows = []
    for t in range(1, TICKS + 1):
        commit_tick(ctx, t)               # apply (t-1) decisions; arm tick
        ctx.snapshot.refresh(ctx.items)   # end-of-(t-1) positions
        se.step(t)
        record(rows, t, ctx.items)        # end-of-t live positions
    return rows


def main():
    tag, path = resolve_scenario(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = sorted(run(path))
    out = os.path.join(os.path.dirname(__file__), f"standalone_{tag}.csv")
    with open(out, "w") as f:
        f.write("tick,object_name,x,y,z\n")
        for r in rows:
            f.write(",".join(str(c) for c in r) + "\n")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
