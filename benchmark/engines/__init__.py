"""Engine adapters for the cross-engine DEVStone comparison.

Each subpackage ships a canonical DEVStone topology built on top of one
simulation engine and a `runner.run(variant, depth, width, ...)` entry point
that returns a `RunResult` from `benchmark.engines.common`.
"""
