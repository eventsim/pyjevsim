"""Reference-engine DEVStone topology — same flat shape as the pyjevsim build."""

from .engine import Atomic, Engine, INFINITY


def _burn(cycles: int) -> int:
    if cycles <= 0:
        return 0
    acc = 0
    for i in range(cycles):
        acc = (acc + i) ^ (i << 1)
    return acc


class DEVStoneAtomic(Atomic):
    __slots__ = ("int_cycles", "ext_cycles",
                 "n_internals", "n_externals", "n_events")

    def __init__(self, name: str, int_cycles: int = 0, ext_cycles: int = 0):
        super().__init__(name)
        self.int_cycles = int_cycles
        self.ext_cycles = ext_cycles
        self.n_internals = 0
        self.n_externals = 0
        self.n_events = 0

    def initialize(self):
        self.sigma = INFINITY
        self.phase = "passive"

    def deltint(self):
        _burn(self.int_cycles)
        self.n_internals += 1
        self.sigma = INFINITY
        self.phase = "passive"

    def deltext(self, e, msgs):
        _burn(self.ext_cycles)
        self.n_externals += 1
        self.n_events += len(msgs)
        self.sigma = 0
        self.phase = "active"

    def lambdaf(self):
        return [0]


class Seeder(Atomic):
    __slots__ = ()

    def initialize(self):
        self.sigma = 0
        self.phase = "active"

    def deltint(self):
        self.sigma = INFINITY
        self.phase = "passive"

    def lambdaf(self):
        return [0]


def build(variant: str, depth: int, width: int,
          int_cycles: int = 0, ext_cycles: int = 0):
    variant = variant.upper()
    if variant not in ("LI", "HI", "HO"):
        raise ValueError(f"variant {variant} not supported")
    if depth < 1 or width < 1:
        raise ValueError("depth and width must be >= 1")

    eng = Engine()
    seeder = eng.add(Seeder("seeder"))

    # 1 atomic at the innermost level + (width-1) atomics per outer level.
    counts = [1] + [width - 1] * (depth - 1)
    levels: list[list[DEVStoneAtomic]] = []
    for d, n in enumerate(counts):
        row = [
            eng.add(DEVStoneAtomic(f"a_d{d}_i{i}", int_cycles, ext_cycles))
            for i in range(n)
        ]
        levels.append(row)

    # Seeder fans out to every atomic.
    for row in levels:
        for atomic in row:
            eng.couple(seeder, atomic)

    if variant in ("HI", "HO"):
        for d in range(1, depth):
            row = levels[d]
            for i in range(len(row) - 1):
                eng.couple(row[i], row[i + 1])

    atomics = [a for row in levels for a in row]
    return eng, atomics, levels
