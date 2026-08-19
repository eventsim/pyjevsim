"""OPTIONAL live Pitch (pRTI 1516e) run of the two-federate anti-torpedo sim.

This is NOT part of the default equivalence gate — verify_equivalence.py uses
only the in-process backend and needs no Java. This script is guarded: a
missing local JPype/JVM/JAR toolchain prints a skip message, while RTI join,
declaration, worker, and cleanup failures propagate as process errors.

Each federate runs in its own thread driving Federate.run_until with
lookahead = 1.0; the local physics is pumped exactly like the in-process
build (commit_tick -> publish_local -> snapshot.refresh -> step), so the
same deterministic 1-tick snapshot discipline applies.

The same driver runs against any registered IEEE 1516-2010 backend; see
run_hla_portico.py, which reuses it with ``backend="portico"``.

Env:
  PYJEVSIM_JVM   path to jvm.dll   (default: Adoptium JDK 11)
  PYJEVSIM_JAR   path to the RTI jar (default: C:\\Program Files\\prti1516e\\lib)
  PYJEVSIM_RTI   backend name      (default: pitch)

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
RTI = os.environ.get("PYJEVSIM_RTI", "pitch")
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
        return f"RTI jar not found at {JAR} (set PYJEVSIM_JAR)"
    return None


def _require_peer_reflection(name, remote, expected_peer_id):
    """Reject a live run that joined an isolated RTI partition."""
    if expected_peer_id not in remote:
        raise RuntimeError(
            f"{name} received no reflection for expected peer "
            f"{expected_peer_id!r} by the first grant; check "
            "RTI_RID_FILE and federation connectivity"
        )


def _raise_worker_errors(worker_errors):
    """Turn a background federate failure into a failing process."""
    if worker_errors:
        name, exc = worker_errors[0]
        raise RuntimeError(f"{name} live-RTI worker failed") from exc


def run(scenario=None, backend=None):
    backend = backend or RTI
    reason = _preflight()
    if reason is not None:
        print(f"[skip] {backend} run not available: {reason}")
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
    from run_standalone_headless import record, SCENARIO
    if scenario is None:
        scenario = SCENARIO

    data = load_scenario(scenario)

    def build_fed(fed_name, model, ctx):
        se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
        ctx.set_executor(se)
        tx = create_rti(
            backend,
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
        try:
            fed.join("AntiTorpedo", fed_name, fom_paths=[FOM])
            fed.publish(PLATFORM_OUT)
            fed.subscribe(PLATFORM_IN)
            se.exec_factory._router.subscribe(
                "attribute", PLATFORM_FOM, ProxySink(ctx)
            )
            return se, tx, fed
        except BaseException:
            try:
                fed.resign()
            except Exception:
                pass
            raise

    ship_ctx, torp_ctx = SimContext(), SimContext()
    ship = build_ship("blue_ship_0", data["SurfaceShip"][0], ship_ctx)
    torp = build_torpedo("red_torpedo_0", data["Torpedo"][0], torp_ctx)

    ship_fed = None
    try:
        ship_se, ship_tx, ship_fed = build_fed("ship", ship, ship_ctx)
        torp_se, torp_tx, torp_fed = build_fed("torpedo", torp, torp_ctx)
    except BaseException:
        if ship_fed is not None:
            try:
                ship_fed.resign()
            except Exception:
                pass
        raise

    rows_lock = threading.Lock()
    errors_lock = threading.Lock()
    rows = []
    worker_errors = []

    def drive(name, se, ctx, tx, expected_peer_id):
        try:
            for t in range(1, TICKS + 1):
                commit_tick(ctx, t)
                publish_local(ctx, tx)
                # request a grant to t (lookahead 1); real RTI blocks until peer
                tx.request_time_advance(float(t))
                if t == 1:
                    _require_peer_reflection(name, ctx.remote, expected_peer_id)
                ctx.snapshot.refresh(list(ctx.items) + list(ctx.remote.values()))
                se.step(t)
                with rows_lock:
                    record(rows, t, ctx.items)
        except BaseException as exc:  # propagate worker failures to the process
            with errors_lock:
                worker_errors.append((name, exc))

    body_failed = False
    try:
        th_s = threading.Thread(
            target=drive,
            args=("ship", ship_se, ship_ctx, ship_tx, torp.sense_id),
        )
        th_t = threading.Thread(
            target=drive,
            args=("torpedo", torp_se, torp_ctx, torp_tx, ship.sense_id),
        )
        th_s.start(); th_t.start()
        th_s.join(); th_t.join()

        _raise_worker_errors(worker_errors)
        return sorted(rows)
    except BaseException:
        body_failed = True
        raise
    finally:
        cleanup_errors = []
        for name, fed in (("ship", ship_fed), ("torpedo", torp_fed)):
            try:
                fed.resign()
            except Exception as exc:  # keep both cleanup attempts observable
                cleanup_errors.append((name, exc))
        if cleanup_errors and not body_failed:
            name, exc = cleanup_errors[0]
            raise RuntimeError(f"{name} federate resign failed") from exc


def main(backend=None):
    backend = backend or RTI
    from run_standalone_headless import resolve_scenario
    tag, path = resolve_scenario(sys.argv[1] if len(sys.argv) > 1 else None)
    rows = run(path, backend)
    if rows is None:
        return
    out = os.path.join(os.path.dirname(__file__), f"hla_{backend}_{tag}.csv")
    with open(out, "w") as f:
        f.write("tick,object_name,x,y,z\n")
        for r in rows:
            f.write(",".join(str(c) for c in r) + "\n")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
