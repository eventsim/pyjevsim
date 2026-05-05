"""Minimal flat-FEL DEVS engine used as a performance floor.

Just enough machinery to run DEVStone:

  - Atomic models with ext_trans, int_trans, output, and a sigma deadline.
  - Atom-to-atom coupling only (we treat the graph as already flattened).
  - A single future-event list keyed by (time, insertion_order).
  - Confluent transitions handled deltint-then-deltext to match xdevs.

Deliberately avoids any abstraction (no Coupled, no Coordinator hierarchy)
so its overhead approximates "writing the simulator inline".
"""

import heapq
import itertools
import math


INFINITY = math.inf


class Atomic:
    """Subclass and override the four DEVS hooks."""

    __slots__ = ("name", "sigma", "phase", "_inputs")

    def __init__(self, name: str):
        self.name = name
        self.sigma = INFINITY
        self.phase = "passive"
        self._inputs: list = []

    # User-overridable -------------------------------------------------------
    def initialize(self):
        pass

    def deltint(self):
        self.sigma = INFINITY
        self.phase = "passive"

    def deltext(self, e: float, msgs: list):
        pass

    def lambdaf(self) -> list:
        return []

    def deltcon(self, msgs: list):
        # Default: deltint then deltext, matching xdevs.
        self.deltint()
        self.deltext(0.0, msgs)


class Engine:
    """Flat DEVS engine with atom-to-atom coupling."""

    def __init__(self):
        self._atomics: list[Atomic] = []
        # coupling: src atomic -> list of dst atomics (single-port model).
        self._couplings: dict[int, list[Atomic]] = {}
        self._fel: list = []
        self._counter = itertools.count()
        self._t_last: dict[int, float] = {}
        self.now = 0.0

    def add(self, atomic: Atomic) -> Atomic:
        self._atomics.append(atomic)
        return atomic

    def couple(self, src: Atomic, dst: Atomic):
        self._couplings.setdefault(id(src), []).append(dst)

    def initialize(self):
        for a in self._atomics:
            a.initialize()
            self._t_last[id(a)] = 0.0
            if a.sigma < INFINITY:
                heapq.heappush(self._fel, (a.sigma, next(self._counter), a))

    def inject(self, target: Atomic, value):
        target._inputs.append(value)
        # Treat injection as an external event at time 0.
        heapq.heappush(self._fel, (0.0, next(self._counter), target))

    def run(self, max_iters: int = 10_000_000):
        fel = self._fel
        couplings = self._couplings
        t_last = self._t_last
        iters = 0
        while fel and iters < max_iters:
            t_next, _, _ = fel[0]
            if t_next == INFINITY:
                break
            self.now = t_next
            # Pop every atomic that fires at this exact time, plus collect
            # any pending input bags so confluent transitions are handled
            # in one pass per atomic.
            firing: dict[int, Atomic] = {}
            while fel and fel[0][0] == t_next:
                _, _, a = heapq.heappop(fel)
                firing[id(a)] = a

            # Phase 1 — collect outputs from atomics whose sigma elapsed.
            outputs: list[tuple[Atomic, list]] = []
            for aid, a in list(firing.items()):
                last = t_last[aid]
                e = self.now - last
                if math.isclose(e, a.sigma) or e >= a.sigma:
                    out = a.lambdaf()
                    if out:
                        outputs.append((a, out))

            # Phase 2 — distribute outputs to receivers and accumulate
            # external events. A receiver may already be in `firing`.
            for src, out in outputs:
                for dst in couplings.get(id(src), ()):
                    dst._inputs.extend(out)
                    if id(dst) not in firing:
                        firing[id(dst)] = dst

            # Phase 3 — drive transitions for every atomic in `firing`.
            for aid, a in firing.items():
                last = t_last[aid]
                e = self.now - last
                has_int = math.isclose(e, a.sigma) or e >= a.sigma
                msgs = a._inputs
                a._inputs = []
                if has_int and msgs:
                    a.deltcon(msgs)
                elif has_int:
                    a.deltint()
                elif msgs:
                    a.deltext(e, msgs)
                t_last[aid] = self.now
                if a.sigma < INFINITY:
                    heapq.heappush(
                        fel, (self.now + a.sigma, next(self._counter), a)
                    )
            iters += 1
        return iters
