"""Live ping-pong against Pitch pRTI (IEEE 1516-2010).

Runs the SAME models as run_inprocess.py, but each paddle is a real federate
joined to a real Pitch federation via the ``pitch`` backend (JPype +
prti1516e). Both federates run in this one process for simplicity; in a real
deployment each would be its own process/host.

Prerequisites:
  * pip install jpype1   (matching your Python; JPype>=1.6 needs Java>=11)
  * Pitch pRTI installed; a CRC running.
  * PRTI_HOME pointing at the install (default: C:\\Program Files\\prti1516e).

Run:  python examples/hla_pingpong/run_pitch.py

The same driver runs against any registered IEEE 1516-2010 backend; see
run_portico.py, which reuses it with ``rti="portico"``. Env overrides:
  PYJEVSIM_RTI   backend name  (default: pitch)
  PYJEVSIM_JAR   RTI jar       (default: $PRTI_HOME/lib/prti1516e.jar)
  PYJEVSIM_JVM   jvm.dll / libjvm.so (optional)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(__file__))

from pingpong_models import (  # noqa: E402
    PINGPONG_FOM_MAP,
    Ping,
    Pong,
    ping_bindings,
    pong_bindings,
)

from pyjevsim import ExecutionType, SysExecutor  # noqa: E402
from pyjevsim.hla import Federate, HLAExecutorFactory, create_rti  # noqa: E402

PRTI_HOME = os.environ.get("PRTI_HOME", r"C:\Program Files\prti1516e")
JAR = os.environ.get("PYJEVSIM_JAR", os.path.join(PRTI_HOME, "lib", "prti1516e.jar"))
RTI = os.environ.get("PYJEVSIM_RTI", "pitch")
FOM = os.path.join(os.path.dirname(__file__), "fom", "PingPong.xml")
# Optional explicit JVM (use a Java>=11 runtime for JPype>=1.6):
JVM_PATH = os.environ.get("PYJEVSIM_JVM")  # e.g. .../jre/bin/server/jvm.dll


def build(model, bindings, name, rti=None):
    se = SysExecutor(_time_resolution=1, ex_mode=ExecutionType.HLA_TIME)
    tx = create_rti(
        rti or RTI,
        federation="PingPong", federate=name,
        fom=FOM, fom_map=PINGPONG_FOM_MAP,
        jvm_path=JVM_PATH, classpath=[JAR], lookahead=1.0,
    )
    se.exec_factory = HLAExecutorFactory(tx, {name: bindings})
    se.register_entity(model)
    se.init_sim()
    return se, Federate(se, tx)


def main(max_volleys: int = 3, end_time: float = 25.0, lookahead: float = 1.0,
         rti: "str | None" = None) -> None:
    import threading

    ping_se, ping_fed = build(Ping("ping", max_volleys=max_volleys),
                              ping_bindings(), "ping", rti)
    pong_se, pong_fed = build(Pong("pong"), pong_bindings(), "pong", rti)

    for fed, name, binds in ((ping_fed, "ping", ping_bindings()),
                             (pong_fed, "pong", pong_bindings())):
        fed.join("PingPong", name, fom_paths=[FOM])
        for b in binds.values():
            if b.direction in ("out", "inout"):
                fed.publish(b)
            if b.direction in ("in", "inout"):
                fed.subscribe(b)
        print(f"{name}: joined + published/subscribed")

    # Two time-managed federates must advance in tandem (each is both
    # regulating and constrained), so each runs in its own thread; the RTI
    # coordinates their time-advance grants and delivers TSO messages.
    t_ping = threading.Thread(target=ping_fed.run_until, args=(end_time, lookahead))
    t_pong = threading.Thread(target=pong_fed.run_until, args=(end_time, lookahead))
    t_ping.start(); t_pong.start()
    t_ping.join(); t_pong.join()

    pong = pong_se.get_entity("pong")[0].get_core_model()
    ping = ping_se.get_entity("ping")[0].get_core_model()
    print("pong received pings:", [d["count"] for d in pong.received_pings])
    print("ping received pongs:", [d["count"] for d in ping.received_pongs])
    print("pong reflected hits:", pong.reflected_hits)
    # `sender` is an HLAunicodeString: printing it proves string fields
    # survive the round trip (they do not on a raw Portico EncoderFactory).
    print("pong ping senders:", [d["sender"] for d in pong.received_pings])

    ping_fed.resign()
    pong_fed.resign()
    print("both federates resigned")


if __name__ == "__main__":
    main()
