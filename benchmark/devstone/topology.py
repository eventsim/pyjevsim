"""
DEVStone topology builders for pyjevsim.

Three canonical variants are implemented (LI, HI, HO). Each builds a flat
graph of registered atomics and couplings inside a SysExecutor:

  Generator -> level_0 -> level_1 -> ... -> level_(depth-1) -> Sink

A "level" is a group of `width - 1` DEVStoneAtomic instances. The first
atomic of the next level acts as that level's input, matching the recursive
"coupled-of-coupled" shape of the original benchmark while keeping the
graph flat for predictable performance.

LI  - Low Interconnect:  level input -> only the first atomic of the level
                         -> next level input.
HI  - High Interconnect: level input -> every atomic of the level; each
                         atomic feeds the next atomic in the level (chain),
                         and the last atomic feeds the next level.
HO  - High Output:       same as HI plus every atomic of the level emits
                         an extra output that goes directly to the sink.

The shape is simple to reason about and exercises the scheduler in the same
ways the literature describes for these variants.
"""

from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor

from .atomic import DEVStoneAtomic, DEVStoneGenerator, DEVStoneSink


def _make_atomic(name, variant, dhrystones):
    if variant == "ho":
        return DEVStoneAtomic(
            name,
            out_ports=("out", "outx"),
            dhrystones=dhrystones,
        )
    return DEVStoneAtomic(name, out_ports=("out",), dhrystones=dhrystones)


def build_devstone(
    variant,
    depth,
    width,
    gen_count,
    gen_period=1.0,
    dhrystones=0,
    time_resolution=1,
):
    """Build a DEVStone simulation.

    Args:
        variant (str): "li", "hi", or "ho".
        depth (int): Number of nested levels (>= 1).
        width (int): Atomics per level (>= 1).
        gen_count (int): Number of events the generator will fire.
        gen_period (float): Time between generator firings.
        dhrystones (int): Synthetic per-event CPU work.
        time_resolution (int): SysExecutor time resolution.

    Returns:
        (SysExecutor, dict): The executor and a dict of model handles useful
        for post-run statistics.
    """
    variant = variant.lower()
    if variant not in {"li", "hi", "ho"}:
        raise ValueError(f"unknown DEVStone variant: {variant}")
    if depth < 1 or width < 1:
        raise ValueError("depth and width must be >= 1")

    ss = SysExecutor(
        time_resolution,
        ex_mode=ExecutionType.V_TIME,
        snapshot_manager=None,
    )

    gen = DEVStoneGenerator("gen", period=gen_period, count=gen_count)
    sink = DEVStoneSink("sink")
    ss.register_entity(gen)
    ss.register_entity(sink)

    levels = []
    for d in range(depth):
        level = [
            _make_atomic(f"a_d{d}_w{w}", variant, dhrystones)
            for w in range(width)
        ]
        for atomic in level:
            ss.register_entity(atomic)
        levels.append(level)

    # Generator -> first atomic of level 0
    ss.coupling_relation(gen, "out", levels[0][0], "in")

    for d, level in enumerate(levels):
        next_input = levels[d + 1][0] if d + 1 < depth else sink

        if variant == "li":
            ss.coupling_relation(level[0], "out", next_input, "in")
        else:
            # HI / HO: chain atomics within the level
            for i in range(width - 1):
                ss.coupling_relation(level[i], "out", level[i + 1], "in")
            ss.coupling_relation(level[-1], "out", next_input, "in")

            # HI / HO: also feed the level input to every atomic to amplify
            # the per-level fan-in (mirrors the high-interconnect property).
            level_input = level[0]
            for i in range(1, width):
                ss.coupling_relation(level_input, "out", level[i], "in")

            if variant == "ho":
                # extra outputs short-circuit straight to the sink
                for atomic in level:
                    ss.coupling_relation(atomic, "outx", sink, "in")

    return ss, {"gen": gen, "sink": sink, "levels": levels}
