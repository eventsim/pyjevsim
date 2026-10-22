"""Seeding of the mwmsim example's random streams (roadmap MA-3)."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "mwmsim_core_component",
    os.path.join(ROOT, "examples", "mwmsim", "core_component.py"))
core_component = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(core_component)


def test_stream_seed_is_deterministic_and_index_dependent():
    assert core_component.stream_seed(0, 0) == core_component.stream_seed(0, 0)
    assert core_component.stream_seed(0, 0) != core_component.stream_seed(0, 1)
    assert core_component.stream_seed(0, 0) != core_component.stream_seed(1, 0)


def test_statistics_draw_reproducible_independent_streams():
    core_component.reset_streams()
    a = core_component.Statistic(0, 10.0, 1.0)
    b = core_component.Statistic(0, 10.0, 1.0)
    first = (a.random.random(), b.random.random())
    assert a.rseed != b.rseed
    core_component.reset_streams()
    a2 = core_component.Statistic(0, 10.0, 1.0)
    b2 = core_component.Statistic(0, 10.0, 1.0)
    assert (a2.rseed, b2.rseed) == (a.rseed, b.rseed)
    assert (a2.random.random(), b2.random.random()) == first
