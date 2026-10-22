"""W4: idle-heavy V_TIME run.

``idle`` passive models (deadline ``Infinite``, never activated) share the
executor with ``pairs`` ping-pong pairs that pass a ball back and forth,
holding it for one tick, until each player has sent ``events // 2`` times.
The idle models are scheduled once at registration and then never touched,
so the run measures how much per-instant work scales with the number of
registered-but-idle models (a dense scheduler degrades badly here).
"""

import time


def _models():
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import Infinite
    from pyjevsim.system_message import SysMessage

    class Idle(BehaviorModel):
        def __init__(self, name):
            super().__init__(name)
            self.insert_state("idle", Infinite)
            self.init_state("idle")
            self.insert_input_port("in")

        def ext_trans(self, port, msg):
            pass

        def int_trans(self):
            pass

        def output(self, msg_deliver):
            pass

    class Player(BehaviorModel):
        """Holds the ball for one tick, then passes it; waits otherwise."""

        def __init__(self, name, serve, limit):
            super().__init__(name)
            self.insert_state("wait", Infinite)
            self.insert_state("hold", 1)
            self.init_state("hold" if serve else "wait")
            self.insert_input_port("in")
            self.insert_output_port("out")
            self.limit = limit
            self.sent = 0
            self.received = 0

        def ext_trans(self, port, msg):
            self.received += 1
            self._cur_state = "hold"

        def int_trans(self):
            self._cur_state = "wait"

        def output(self, msg_deliver):
            if self.sent < self.limit:
                self.sent += 1
                m = SysMessage(self.get_name(), "out")
                m.insert(self.sent)
                msg_deliver.insert_message(m)

    return Idle, Player


def run_idle(params):
    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor

    n_idle, pairs, events = (int(params["idle"]), int(params["pairs"]),
                             int(params["events"]))
    Idle, Player = _models()

    t0 = time.perf_counter()
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    for i in range(n_idle):
        ss.register_entity(Idle(f"idle{i}"))
    players = []
    for k in range(pairs):
        a = Player(f"a{k}", True, events // 2)
        b = Player(f"b{k}", False, events // 2)
        ss.register_entity(a)
        ss.register_entity(b)
        ss.coupling_relation(a, "out", b, "in")
        ss.coupling_relation(b, "out", a, "in")
        players += [a, b]
    t1 = time.perf_counter()
    ss.simulate(events + 5, _tm=False)
    t2 = time.perf_counter()

    return {
        "metrics": {"sim_s": t2 - t1},
        "build_s": t1 - t0,
        "parity": {"sent": sum(p.sent for p in players),
                   "received": sum(p.received for p in players),
                   "global_time": ss.global_time},
        "info": {"models": n_idle + 2 * pairs},
    }
