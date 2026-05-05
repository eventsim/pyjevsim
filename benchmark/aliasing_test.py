"""Empirical multi-subscriber output aliasing test.

Setup
-----
A producer emits ONE message — a mutable list `[1, 2, 3]` — through a single
output port that is fanned out to TWO subscriber atomics. Each subscriber
appends its own tag ("A" / "B") to the list it receives.

After the simulation completes we inspect:

  * each subscriber's own snapshot taken on entry (order-dependent),
  * the producer's reference to the original list (order-independent).

If the engine shares the value reference across receivers, the producer's
list ends as `[1, 2, 3, 'A', 'B']` (or `[1, 2, 3, 'B', 'A']`).
If the engine copies per receiver, the producer's list stays `[1, 2, 3]`.

Run with:

    python -m benchmark.aliasing_test
"""

from __future__ import annotations

import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# pyjevsim
# ---------------------------------------------------------------------------

def test_pyjevsim() -> dict:
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.system_message import SysMessage

    snapshots = {"A": None, "B": None}
    producer_payload_holder = {"ref": None}

    class Producer(BehaviorModel):
        def __init__(self):
            super().__init__("producer")
            self.insert_state("active", 0)
            self.insert_state("done")
            self.init_state("active")
            self.insert_output_port("out")

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            if self._cur_state == "active":
                self._cur_state = "done"

        def output(self, msg_deliver):
            if self._cur_state == "active":
                payload = [1, 2, 3]
                producer_payload_holder["ref"] = payload
                m = SysMessage(self.get_name(), "out")
                m.insert(payload)
                msg_deliver.insert_message(m)

    class Subscriber(BehaviorModel):
        def __init__(self, name, tag):
            super().__init__(name)
            self.insert_state("passive")
            self.init_state("passive")
            self.insert_input_port("in")
            self._tag = tag

        def ext_trans(self, port, msg):
            payload = msg.retrieve()[0]
            snapshots[self._tag] = list(payload)
            payload.append(self._tag)

        def int_trans(self):
            pass

        def output(self, msg_deliver):
            pass

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    prod = Producer()
    sub_a = Subscriber("subA", "A")
    sub_b = Subscriber("subB", "B")

    ss.register_entity(prod)
    ss.register_entity(sub_a)
    ss.register_entity(sub_b)
    ss.coupling_relation(prod, "out", sub_a, "in")
    ss.coupling_relation(prod, "out", sub_b, "in")
    ss.simulate(2, _tm=False)

    return {
        "A_snapshot": snapshots["A"],
        "B_snapshot": snapshots["B"],
        "producer_final": producer_payload_holder["ref"],
    }


# ---------------------------------------------------------------------------
# xdevs
# ---------------------------------------------------------------------------

def test_xdevs() -> dict:
    from xdevs.models import Atomic, Coupled, Port
    from xdevs.sim import Coordinator

    snapshots = {"A": None, "B": None}
    producer_payload_holder = {"ref": None}

    class Producer(Atomic):
        def __init__(self):
            super().__init__("producer")
            self.o = Port(list, "o")
            self.add_out_port(self.o)

        def initialize(self):
            self.activate()

        def deltint(self):
            self.passivate()

        def deltext(self, e):
            pass

        def lambdaf(self):
            payload = [1, 2, 3]
            producer_payload_holder["ref"] = payload
            self.o.add(payload)

        def exit(self):
            pass

    class Subscriber(Atomic):
        def __init__(self, name, tag):
            super().__init__(name)
            self.i = Port(list, "i")
            self.add_in_port(self.i)
            self._tag = tag

        def initialize(self):
            self.passivate()

        def deltint(self):
            pass

        def deltext(self, e):
            for payload in self.i.values:
                snapshots[self._tag] = list(payload)
                payload.append(self._tag)
            self.passivate()

        def lambdaf(self):
            pass

        def exit(self):
            pass

    class Root(Coupled):
        def __init__(self):
            super().__init__("root")
            self.p = Producer()
            self.a = Subscriber("a", "A")
            self.b = Subscriber("b", "B")
            self.add_component(self.p)
            self.add_component(self.a)
            self.add_component(self.b)
            self.add_coupling(self.p.o, self.a.i)
            self.add_coupling(self.p.o, self.b.i)

    coord = Coordinator(Root())
    coord.initialize()
    coord.simulate(num_iters=10)
    return {
        "A_snapshot": snapshots["A"],
        "B_snapshot": snapshots["B"],
        "producer_final": producer_payload_holder["ref"],
    }


# ---------------------------------------------------------------------------
# pypdevs (minimal kernel)
# ---------------------------------------------------------------------------

def test_pypdevs() -> dict:
    from pypdevs.minimal import AtomicDEVS, CoupledDEVS, Simulator

    snapshots = {"A": None, "B": None}
    producer_payload_holder = {"ref": None}
    INF = float("inf")

    class Producer(AtomicDEVS):
        def __init__(self):
            super().__init__("producer")
            self.state = "active"
            self.outp = self.addOutPort("out")

        def timeAdvance(self):
            return 0.0 if self.state == "active" else INF

        def intTransition(self):
            return "done"

        def outputFnc(self):
            payload = [1, 2, 3]
            producer_payload_holder["ref"] = payload
            return {self.outp: [payload]}

    class Subscriber(AtomicDEVS):
        def __init__(self, name, tag):
            super().__init__(name)
            self.state = "passive"
            self.inp = self.addInPort("in")
            self._tag = tag

        def timeAdvance(self):
            return INF

        def extTransition(self, inputs):
            for port_msgs in inputs.values():
                for payload in port_msgs:
                    snapshots[self._tag] = list(payload)
                    payload.append(self._tag)
            return "passive"

    class Root(CoupledDEVS):
        def __init__(self):
            super().__init__("root")
            self.p = self.addSubModel(Producer())
            self.a = self.addSubModel(Subscriber("a", "A"))
            self.b = self.addSubModel(Subscriber("b", "B"))
            self.connectPorts(self.p.outp, self.a.inp)
            self.connectPorts(self.p.outp, self.b.inp)

    sim = Simulator(Root())
    sim.setTerminationTime(2)
    sim.simulate()
    return {
        "A_snapshot": snapshots["A"],
        "B_snapshot": snapshots["B"],
        "producer_final": producer_payload_holder["ref"],
    }


# ---------------------------------------------------------------------------
# reference engine
# ---------------------------------------------------------------------------

def test_reference() -> dict:
    from benchmark.engines.reference.engine import Atomic, Engine, INFINITY

    snapshots = {"A": None, "B": None}
    producer_payload_holder = {"ref": None}

    class Producer(Atomic):
        __slots__ = ()

        def initialize(self):
            self.sigma = 0.0
            self.phase = "active"

        def deltint(self):
            self.sigma = INFINITY
            self.phase = "passive"

        def lambdaf(self):
            payload = [1, 2, 3]
            producer_payload_holder["ref"] = payload
            return [payload]

    class Subscriber(Atomic):
        __slots__ = ("tag",)

        def __init__(self, name, tag):
            super().__init__(name)
            self.tag = tag

        def deltext(self, e, msgs):
            for payload in msgs:
                snapshots[self.tag] = list(payload)
                payload.append(self.tag)
            self.sigma = INFINITY

    eng = Engine()
    p = eng.add(Producer("p"))
    a = eng.add(Subscriber("a", "A"))
    b = eng.add(Subscriber("b", "B"))
    eng.couple(p, a)
    eng.couple(p, b)
    eng.initialize()
    eng.run()
    return {
        "A_snapshot": snapshots["A"],
        "B_snapshot": snapshots["B"],
        "producer_final": producer_payload_holder["ref"],
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def diagnose(name, fn):
    try:
        r = fn()
    except Exception as exc:
        print(f"{name:>10}  ERROR: {type(exc).__name__}: {exc}")
        return
    a, b, p = r["A_snapshot"], r["B_snapshot"], r["producer_final"]
    # If both subscribers' tags ended up in the producer's reference, the
    # engines is sharing the value across receivers. If neither appears (or
    # at most one appears because that subscriber happens to share with the
    # producer's outport directly), the engine is copying.
    seen_in_producer = sum(t in (p or []) for t in ("A", "B"))
    if seen_in_producer == 2:
        verdict = "ALIASED - both subscribers mutate the same object"
    elif seen_in_producer == 1:
        verdict = "PARTIALLY aliased - one subscriber shares with producer outport"
    else:
        verdict = "isolated - per-receiver copy"
    print(f"{name:>10}  A_snap={a}  B_snap={b}  prod_final={p}")
    print(f"{'':>10}    -> {verdict}")


if __name__ == "__main__":
    print("Multi-subscriber output aliasing test\n"
          "  producer emits [1,2,3]; subscriber A appends 'A', B appends 'B'\n")
    for name, fn in [
        ("pyjevsim", test_pyjevsim),
        ("xdevs", test_xdevs),
        ("pypdevs", test_pypdevs),
        ("reference", test_reference),
    ]:
        diagnose(name, fn)
