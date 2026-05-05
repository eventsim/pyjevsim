"""DEVStone topology built on PythonPDEVS's minimal kernel.

The minimal kernel (`pypdevs.minimal`) is the recommended local-simulation
backend per the upstream README. The graph here matches the same flat shape
used by the pyjevsim and reference adapters: a Seeder fans out one event to
every atomic, and HI/HO additionally chain atomics within each non-innermost
level.

Implementation notes
--------------------

- The minimal kernel hard-codes `intTransition` to use the *previous* state,
  so we mutate the atomic's `self.state` dictionary in-place inside the
  transition methods and return it.
- Counters live on the atomic object (`n_internals`, `n_externals`,
  `n_events`) and are read after `simulate()` returns.
"""

from pypdevs.minimal import AtomicDEVS, CoupledDEVS

INFINITY = float("inf")


def _burn(cycles: int) -> int:
    if cycles <= 0:
        return 0
    acc = 0
    for i in range(cycles):
        acc = (acc + i) ^ (i << 1)
    return acc


class DEVStoneAtomic(AtomicDEVS):
    def __init__(self, name: str, int_cycles: int = 0, ext_cycles: int = 0):
        super().__init__(name)
        self.int_cycles = int_cycles
        self.ext_cycles = ext_cycles
        self.n_internals = 0
        self.n_externals = 0
        self.n_events = 0

        self.in_port = self.addInPort("in")
        self.out_port = self.addOutPort("out")

        self.state = "passive"
        self.elapsed = 0.0

    def timeAdvance(self):
        return 0.0 if self.state == "active" else INFINITY

    def intTransition(self):
        _burn(self.int_cycles)
        self.n_internals += 1
        return "passive"

    def extTransition(self, inputs):
        _burn(self.ext_cycles)
        self.n_externals += 1
        for port_msgs in inputs.values():
            self.n_events += len(port_msgs)
        return "active"

    def confTransition(self, inputs):
        # Default DEVS confluent: int then ext, matching xdevs.
        self.state = self.intTransition()
        return self.extTransition(inputs)

    def outputFnc(self):
        return {self.out_port: [0]}


class Seeder(AtomicDEVS):
    """One-shot generator: fires once at t=0 then passivates."""

    def __init__(self, name: str = "seeder"):
        super().__init__(name)
        self.out_port = self.addOutPort("out")
        self.state = "active"
        self.elapsed = 0.0

    def timeAdvance(self):
        return 0.0 if self.state == "active" else INFINITY

    def intTransition(self):
        return "done"

    def outputFnc(self):
        return {self.out_port: [0]}


class DEVStoneRoot(CoupledDEVS):
    def __init__(self, variant: str, depth: int, width: int,
                 int_cycles: int = 0, ext_cycles: int = 0):
        super().__init__(f"{variant}_root")
        variant = variant.upper()
        if variant not in ("LI", "HI", "HO"):
            raise ValueError(f"variant {variant} not supported")

        self.seeder = self.addSubModel(Seeder("seeder"))

        counts = [1] + [width - 1] * (depth - 1)
        self.levels: list[list[DEVStoneAtomic]] = []
        for d, n in enumerate(counts):
            row = []
            for i in range(n):
                atomic = self.addSubModel(
                    DEVStoneAtomic(f"a_d{d}_i{i}", int_cycles, ext_cycles)
                )
                row.append(atomic)
            self.levels.append(row)

        # Seeder fans out to every atomic.
        for row in self.levels:
            for atomic in row:
                self.connectPorts(self.seeder.out_port, atomic.in_port)

        # HI / HO add an intra-level chain in every non-innermost level.
        if variant in ("HI", "HO"):
            for d in range(1, depth):
                row = self.levels[d]
                for i in range(len(row) - 1):
                    self.connectPorts(row[i].out_port, row[i + 1].in_port)

        self.atomics = [a for row in self.levels for a in row]
