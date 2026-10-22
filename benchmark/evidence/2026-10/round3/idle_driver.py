"""Idle-heavy V_TIME timing driver: N passive idle models + active ping-pong pairs.

Usage: python idle_driver.py --repo <checkout> [--idle 10000] [--pairs 5] [--events 100]
Prints one JSON line: elapsed wall time of simulate() plus counters.
"""
import argparse, json, os, sys, time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--idle", type=int, default=10000)
    p.add_argument("--pairs", type=int, default=5)
    p.add_argument("--events", type=int, default=100)
    a = p.parse_args()
    repo = os.path.abspath(a.repo)
    sys.path.insert(0, repo)
    import pyjevsim
    assert os.path.abspath(pyjevsim.__file__).startswith(repo)
    from pyjevsim.behavior_model import BehaviorModel
    from pyjevsim.definition import ExecutionType, Infinite
    from pyjevsim.system_executor import SysExecutor
    from pyjevsim.system_message import SysMessage

    class Idle(BehaviorModel):
        def __init__(self, name):
            super().__init__(name)
            self.insert_state("idle", Infinite)
            self.init_state("idle")
            self.insert_input_port("in")
        def ext_trans(self, port, msg): pass
        def int_trans(self): pass
        def output(self, md): pass

    class Player(BehaviorModel):
        """Holds the ball for 1 tick, then passes it; waits passively otherwise."""
        def __init__(self, name, serve, limit):
            super().__init__(name)
            self.insert_state("wait", Infinite)
            self.insert_state("hold", 1)
            self.init_state("hold" if serve else "wait")
            self.insert_input_port("in")
            self.insert_output_port("out")
            self.limit = limit
            self.sent = 0
        def ext_trans(self, port, msg):
            self._cur_state = "hold"
        def int_trans(self):
            self._cur_state = "wait"
        def output(self, md):
            if self.sent < self.limit:
                self.sent += 1
                m = SysMessage(self.get_name(), "out")
                m.insert(self.sent)
                md.insert_message(m)

    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    for i in range(a.idle):
        ss.register_entity(Idle(f"idle{i}"))
    players = []
    for k in range(a.pairs):
        x = Player(f"a{k}", True, a.events // 2)
        y = Player(f"b{k}", False, a.events // 2)
        ss.register_entity(x); ss.register_entity(y)
        ss.coupling_relation(x, "out", y, "in")
        ss.coupling_relation(y, "out", x, "in")
        players += [x, y]
    t0 = time.perf_counter()
    ss.simulate(a.events + 5, _tm=False)
    el = time.perf_counter() - t0
    print(json.dumps({"elapsed_s": round(el, 6), "sent": sum(p.sent for p in players),
                      "global_time": ss.global_time}))


if __name__ == "__main__":
    main()
