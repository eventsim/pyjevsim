"""HLA in-process run: two federates (surfaceship + torpedo) in lockstep.

No Java / pRTI required. Two SysExecutors join one InProcessFederation and
exchange Platform positions with lookahead = 1 tick via an explicit
tick-boundary pipeline. Produces a CSV identical to the standalone run.

Run:  python examples/hla_atsim/run_hla_inprocess.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402
from pyjevsim.hla import (  # noqa: E402
    Federate,
    HLAExecutorFactory,
    InProcessFederation,
    InProcessRTI,
)

from utils.sim_context import SimContext  # noqa: E402
from utils.builder import load_scenario, build_ship, build_torpedo  # noqa: E402
from utils.ticking import commit_tick  # noqa: E402
from hla_common import (  # noqa: E402
    PLATFORM_FOM,
    PLATFORM_OUT,
    PLATFORM_IN,
    ProxySink,
    publish_local,
)
from run_standalone_headless import record, SCENARIO, TICKS, resolve_scenario  # noqa: E402

FOM = os.path.join(os.path.dirname(__file__), "fom", "AntiTorpedo.xml")


def build_fed(fed_name, model, ctx, federation):
    se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
    ctx.set_executor(se)

    tx = InProcessRTI(federation=federation)
    # Empty bindings -> every model gets a plain BehaviorExecutor (pure DEVS);
    # position exchange is pumped explicitly at the tick boundary.
    se.exec_factory = HLAExecutorFactory(tx, {})

    se.insert_input_port("start")
    se.register_entity(model)
    se.coupling_relation(se, "start", model, "start")
    se.init_sim()
    se.insert_external_event("start", None)

    fed = Federate(se, tx)
    fed.join("AntiTorpedo", fed_name, fom_paths=[FOM])
    fed.publish(PLATFORM_OUT)
    fed.subscribe(PLATFORM_IN)

    # Reuse the factory's router; add a synchronous proxy sink that upserts
    # reflected peer/decoy positions into ctx.remote.
    se.exec_factory._router.subscribe("attribute", PLATFORM_FOM, ProxySink(ctx))
    return se, tx, fed


def run(scenario=SCENARIO):
    federation = InProcessFederation("AntiTorpedo")
    data = load_scenario(scenario)

    ship_ctx, torp_ctx = SimContext(), SimContext()
    ship = build_ship("blue_ship_0", data["SurfaceShip"][0], ship_ctx)
    torp = build_torpedo("red_torpedo_0", data["Torpedo"][0], torp_ctx)

    ship_se, ship_tx, ship_fed = build_fed("ship", ship, ship_ctx, federation)
    torp_se, torp_tx, torp_fed = build_fed("torpedo", torp, torp_ctx, federation)
    print(f"federation members after join: {len(federation.members)}")

    rows = []
    for t in range(1, TICKS + 1):
        # Phase 0: commit each federate's (t-1) decisions; arm the tick.
        commit_tick(ship_ctx, t)
        commit_tick(torp_ctx, t)
        # Phase 1: publish end-of-(t-1) positions; the in-process broadcast
        #          synchronously updates the PEER ctx.remote via ProxySink.
        publish_local(ship_ctx, ship_tx)   # -> torp_ctx.remote gets ship + decoys
        publish_local(torp_ctx, torp_tx)   # -> ship_ctx.remote gets torpedo
        # Phase 2: each snapshot = local items + reflected remote peers.
        ship_ctx.snapshot.refresh(list(ship_ctx.items) + list(ship_ctx.remote.values()))
        torp_ctx.snapshot.refresh(list(torp_ctx.items) + list(torp_ctx.remote.values()))
        # Phase 3: advance each federate one tick (no cross-fed interaction now).
        ship_se.step(t)
        torp_se.step(t)
        # Phase 4: record LOCAL live positions from both federates.
        record(rows, t, ship_ctx.items)
        record(rows, t, torp_ctx.items)

    ship_fed.resign()
    torp_fed.resign()
    print(f"federation members after resign: {len(federation.members)}")
    return rows


def main():
    tag, path = resolve_scenario(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = sorted(run(path))
    out = os.path.join(os.path.dirname(__file__), f"hla_{tag}.csv")
    with open(out, "w") as f:
        f.write("tick,object_name,x,y,z\n")
        for r in rows:
            f.write(",".join(str(c) for c in r) + "\n")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
