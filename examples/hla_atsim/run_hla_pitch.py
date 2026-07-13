"""OPTIONAL live Pitch (pRTI 1516e) run of the two-federate anti-torpedo sim.

This is NOT part of the equivalence gate — the gate (verify_equivalence.py)
uses only the in-process backend and needs no Java. This script is a
best-effort bridge to a real RTI and is guarded: if the JVM / prti1516e.jar
/ a reachable CRC are not available it prints a skip message and exits 0.

Each federate runs in its own thread driving Federate.run_until with
lookahead = 1.0; the local physics is pumped exactly like the in-process
build (commit_tick -> publish_local -> snapshot.refresh -> step), so the
same deterministic 1-tick snapshot discipline applies.

Env:
  PYJEVSIM_JVM   path to jvm.dll   (default: Adoptium JDK 11)
  PYJEVSIM_JAR   path to prti1516e.jar (default: C:\\Program Files\\prti1516e\\lib)

Run:  python examples/hla_atsim/run_hla_pitch.py
"""

from __future__ import annotations

import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

FOM = os.path.join(os.path.dirname(__file__), "fom", "AntiTorpedo.xml")

JVM_PATH = os.environ.get(
    "PYJEVSIM_JVM",
    r"C:\Program Files\Eclipse Adoptium\jdk-11.0.31.11-hotspot\bin\server\jvm.dll",
)
JAR = os.environ.get(
    "PYJEVSIM_JAR",
    r"C:\Program Files\prti1516e\lib\prti1516e.jar",
)
TICKS = 30


def _preflight():
    """Return None if runnable, else a human-readable skip reason."""
    try:
        import jpype  # noqa: F401
    except Exception as e:
        return f"jpype not importable ({e})"
    if not os.path.exists(JVM_PATH):
        return f"JVM not found at {JVM_PATH} (set PYJEVSIM_JVM)"
    if not os.path.exists(JAR):
        return f"prti1516e.jar not found at {JAR} (set PYJEVSIM_JAR)"
    return None


def run(scenario=None):
    reason = _preflight()
    if reason is not None:
        print(f"[skip] Pitch run not available: {reason}")
        return None

    from pyjevsim import ExecutionType, SysExecutor
    from pyjevsim.hla import Federate, HLAExecutorFactory, create_rti

    from utils.sim_context import SimContext
    from utils.builder import load_scenario, build_ship, build_torpedo
    from utils.ticking import commit_tick
    from hla_common import (
        PLATFORM_FOM, PLATFORM_OUT, PLATFORM_IN,
        ANTITORPEDO_FOM_MAP, ProxySink, publish_local,
    )
    from run_standalone_headless import record, SCENARIO, resolve_scenario
    if scenario is None:
        scenario = SCENARIO

    data = load_scenario(scenario)

    def build_fed(fed_name, model, ctx):
        se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
        ctx.set_executor(se)
        tx = create_rti(
            "pitch",
            federation="AntiTorpedo",
            federate=fed_name,
            fom=FOM,
            fom_map=ANTITORPEDO_FOM_MAP,
            jvm_path=JVM_PATH,
            classpath=[JAR],
            lookahead=1.0,
        )
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
        se.exec_factory._router.subscribe("attribute", PLATFORM_FOM, ProxySink(ctx))
        return se, tx, fed

    ship_ctx, torp_ctx = SimContext(), SimContext()
    ship = build_ship("blue_ship_0", data["SurfaceShip"][0], ship_ctx)
    torp = build_torpedo("red_torpedo_0", data["Torpedo"][0], torp_ctx)

    try:
        ship_se, ship_tx, ship_fed = build_fed("ship", ship, ship_ctx)
        torp_se, torp_tx, torp_fed = build_fed("torpedo", torp, torp_ctx)
    except Exception as e:
        print(f"[skip] could not join federation (CRC not reachable?): {e}")
        return None

    rows_lock = threading.Lock()
    rows = []

    def drive(se, ctx, tx, other_ready):
        for t in range(1, TICKS + 1):
            commit_tick(ctx, t)
            publish_local(ctx, tx)
            # request a grant to t (lookahead 1); real RTI blocks until peer
            tx.request_time_advance(float(t))
            ctx.snapshot.refresh(list(ctx.items) + list(ctx.remote.values()))
            se.step(t)
            with rows_lock:
                record(rows, t, ctx.items)

    th_s = threading.Thread(target=drive, args=(ship_se, ship_ctx, ship_tx, None))
    th_t = threading.Thread(target=drive, args=(torp_se, torp_ctx, torp_tx, None))
    th_s.start(); th_t.start()
    th_s.join(); th_t.join()

    ship_fed.resign(); torp_fed.resign()
    return sorted(rows)


def main():
    from run_standalone_headless import resolve_scenario
    tag, path = resolve_scenario(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = run(path)
    if rows is None:
        return
    out = os.path.join(os.path.dirname(__file__), f"hla_pitch_{tag}.csv")
    with open(out, "w") as f:
        f.write("tick,object_name,x,y,z\n")
        for r in rows:
            f.write(",".join(str(c) for c in r) + "\n")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
