"""Live GORTI run of the two-federate anti-torpedo simulation.

The model, FOM, tick discipline, and 180-row comparison criterion are the
same as the Pitch and Portico runners.  This adapter uses GORTI's native
Python SDK, so Java and JPype are not required.

Environment:
  GORTI_URL                  rtid endpoint (default grpc://127.0.0.1:8442)
  GORTI_RTID                 optional path to rtid; when set, this script
                             starts and stops that process itself
  GORTI_TIME_ADVANCE_TIMEOUT seconds per time-advance grant (default 30)

Run:
  python examples/hla_atsim/run_hla_gorti.py [scenario]
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

FOM = HERE / "fom" / "AntiTorpedo.xml"
GORTI_URL = os.environ.get("GORTI_URL", "grpc://127.0.0.1:8442")
GORTI_RTID = os.environ.get("GORTI_RTID", "")
GRANT_TIMEOUT = float(os.environ.get("GORTI_TIME_ADVANCE_TIMEOUT", "30"))
TICKS = 30


def _endpoint(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme != "grpc" or parsed.hostname is None:
        raise ValueError(
            "GORTI_URL must be a grpc://host:port endpoint for a live run"
        )
    return parsed.hostname, parsed.port or 8442


def _wait_for_endpoint(url: str, timeout: float = 10.0) -> bool:
    host, port = _endpoint(url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.25)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.05)
    return False


@contextmanager
def _managed_rtid(url: str):
    """Optionally own one local rtid process for this scenario run."""
    if not GORTI_RTID:
        yield None
        return
    binary = Path(GORTI_RTID).expanduser().resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"GORTI_RTID not found: {binary}")
    host, port = _endpoint(url)
    if _wait_for_endpoint(url, timeout=0.2):
        raise RuntimeError(
            f"cannot start managed rtid: {url} is already accepting connections"
        )
    with tempfile.TemporaryDirectory(prefix="pyjevsim-gorti-rtid-") as run_dir:
        run_path = Path(run_dir)
        proc = subprocess.Popen(
            [
                str(binary),
                "--listen", f"{host}:{port}",
                "--metrics-listen", "127.0.0.1:0",
                "--admin-listen", "",
                "--save-dir", str(run_path / "saves"),
                "--state-dir", str(run_path / "state"),
                "--log-level", "warn",
            ],
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            available = _wait_for_endpoint(url)
            if not available or proc.poll() is not None:
                if proc.poll() is None:
                    proc.terminate()
                stdout, stderr = proc.communicate(timeout=5)
                raise RuntimeError(
                    "rtid did not accept connections within 10 seconds\n"
                    f"stdout: {stdout[-2000:]}\nstderr: {stderr[-2000:]}"
                )
            yield proc
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


def _preflight(url: str) -> str | None:
    try:
        import rti1516e  # noqa: F401
    except Exception as exc:
        return f"rti1516e SDK not importable ({exc})"
    if GRANT_TIMEOUT <= 0:
        return "GORTI_TIME_ADVANCE_TIMEOUT must be positive"
    try:
        available = _wait_for_endpoint(url, timeout=1.0)
    except ValueError as exc:
        return str(exc)
    if not available:
        return (
            f"rtid is not reachable at {url}; start it first or set "
            "GORTI_RTID to a local rtid executable"
        )
    return None


def _require_peer_reflection(name, remote, expected_peer_id):
    if expected_peer_id not in remote:
        raise RuntimeError(
            f"{name} received no reflection for expected peer "
            f"{expected_peer_id!r} by the first grant"
        )


def run(scenario, *, url: str = GORTI_URL):
    from pyjevsim import ExecutionType, SysExecutor
    from pyjevsim.hla import Federate, HLAExecutorFactory, create_rti

    from hla_common import (
        ANTITORPEDO_FOM_MAP,
        PLATFORM_FOM,
        PLATFORM_IN,
        PLATFORM_OUT,
        ProxySink,
        publish_local,
    )
    from run_standalone_headless import record
    from utils.builder import build_ship, build_torpedo, load_scenario
    from utils.sim_context import SimContext
    from utils.ticking import commit_tick

    data = load_scenario(scenario)
    federation_name = os.environ.get("GORTI_FEDERATION", "AntiTorpedoGorti")
    transports = []
    federates = []

    def build_fed(fed_name, model, ctx):
        se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
        ctx.set_executor(se)
        tx = create_rti(
            "gorti",
            federation=federation_name,
            federate=fed_name,
            fom=str(FOM),
            fom_map=ANTITORPEDO_FOM_MAP,
            url=url,
            lookahead=1.0,
            time_advance_timeout=GRANT_TIMEOUT,
        )
        transports.append(tx)
        se.exec_factory = HLAExecutorFactory(tx, {})
        se.insert_input_port("start")
        se.register_entity(model)
        se.coupling_relation(se, "start", model, "start")
        se.init_sim()
        se.insert_external_event("start", None)
        fed = Federate(se, tx)
        federates.append(fed)
        fed.join(federation_name, fed_name, fom_paths=[str(FOM)])
        fed.publish(PLATFORM_OUT)
        fed.subscribe(PLATFORM_IN)
        se.exec_factory._router.subscribe(
            "attribute", PLATFORM_FOM, ProxySink(ctx)
        )
        return se, tx

    ship_ctx, torpedo_ctx = SimContext(), SimContext()
    ship = build_ship("blue_ship_0", data["SurfaceShip"][0], ship_ctx)
    torpedo = build_torpedo("red_torpedo_0", data["Torpedo"][0], torpedo_ctx)
    rows = []
    rows_lock = threading.Lock()
    errors_lock = threading.Lock()
    worker_errors = []

    try:
        ship_se, ship_tx = build_fed("ship", ship, ship_ctx)
        torpedo_se, torpedo_tx = build_fed("torpedo", torpedo, torpedo_ctx)

        def drive(name, se, ctx, tx, expected_peer_id):
            try:
                for tick in range(1, TICKS + 1):
                    commit_tick(ctx, tick)
                    publish_local(ctx, tx)
                    granted = tx.request_time_advance(float(tick))
                    if granted != float(tick):
                        raise RuntimeError(
                            f"{name} requested {tick}, received grant {granted}"
                        )
                    if tick == 1:
                        _require_peer_reflection(
                            name, ctx.remote, expected_peer_id
                        )
                    ctx.snapshot.refresh(
                        list(ctx.items) + list(ctx.remote.values())
                    )
                    se.step(tick)
                    with rows_lock:
                        record(rows, tick, ctx.items)
            except BaseException as exc:
                with errors_lock:
                    worker_errors.append((name, exc))

        threads = [
            threading.Thread(
                target=drive,
                args=("ship", ship_se, ship_ctx, ship_tx, torpedo.sense_id),
            ),
            threading.Thread(
                target=drive,
                args=(
                    "torpedo", torpedo_se, torpedo_ctx, torpedo_tx,
                    ship.sense_id,
                ),
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if worker_errors:
            name, exc = worker_errors[0]
            raise RuntimeError(f"{name} GORTI worker failed") from exc
        return sorted(rows)
    finally:
        for fed in reversed(federates):
            with contextlib.suppress(Exception):
                fed.resign()
        # Federate.resign() ends federation membership; close() is still
        # required to stop each SDK ambassador loop and gRPC connection.
        for tx in reversed(transports):
            with contextlib.suppress(Exception):
                tx.close()


def main() -> None:
    from run_standalone_headless import resolve_scenario

    tag, path = resolve_scenario(sys.argv[1] if len(sys.argv) > 1 else None)
    try:
        with _managed_rtid(GORTI_URL):
            reason = _preflight(GORTI_URL)
            if reason is not None:
                print(f"[skip] gorti run not available: {reason}")
                return
            rows = run(path, url=GORTI_URL)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[error] gorti setup failed: {exc}", file=sys.stderr)
        raise

    out = HERE / f"hla_gorti_{tag}.csv"
    with out.open("w", encoding="utf-8", newline="") as stream:
        stream.write("tick,object_name,x,y,z\n")
        for row in rows:
            stream.write(",".join(str(value) for value in row) + "\n")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
