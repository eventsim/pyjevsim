"""Direct model-contract tests for the AT/SIM RL-controlled surface ship."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

from pyjevsim.definition import ExecutionType
from pyjevsim.system_executor import SysExecutor


AT_SIM_ROOT = Path(__file__).resolve().parents[1] / "examples" / "hla_atsim"
if str(AT_SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(AT_SIM_ROOT))

from model.launcher import Launcher  # noqa: E402
from model.manuever import Manuever  # noqa: E402
from model.rl_command_control import ACTION_COMMANDS, decode_action  # noqa: E402
from model.rl_surfaceship import RLSurfaceShip  # noqa: E402
from utils.sim_context import SimContext  # noqa: E402
from utils.ticking import commit_tick  # noqa: E402


SHIP_SCENARIO = {
    "ManueverObject": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "heading": 0.0,
        "xy_speed": 3.0,
        "z_speed": 0.0,
    },
    "LauncherObject": {
        "DecoyObjects": [
            {
                "type": "self_propelled",
                "elevation": 45.0,
                "azimuth": azimuth,
                "speed": 10.0,
                "lifespan": 10.0,
                "heading": azimuth,
                "xy_speed": 2.0,
            }
            for azimuth in (45.0, 135.0, 225.0, 315.0)
        ]
    },
}


def _build_graph() -> tuple[SysExecutor, SimContext, RLSurfaceShip]:
    context = SimContext()
    executor = SysExecutor(
        1.0,
        ex_mode=ExecutionType.HLA_TIME,
        snapshot_manager=None,
    )
    context.set_executor(executor)
    ship = RLSurfaceShip("blue_ship_0", SHIP_SCENARIO, context)

    executor.insert_input_port("start")
    executor.insert_input_port("rl_action")
    executor.register_entity(ship)
    executor.coupling_relation(None, "start", ship, "start")
    executor.coupling_relation(None, "rl_action", ship, "rl_action")
    executor.init_sim()
    executor.insert_external_event("start", None, scheduled_time=0.0)
    executor.step(0.0)
    context.snapshot.refresh(context.items)
    return executor, context, ship


def _step_action(
    executor: SysExecutor,
    context: SimContext,
    action: int,
) -> None:
    next_tick = int(executor.get_global_time()) + 1
    commit_tick(context, next_tick)
    context.snapshot.refresh(context.items)
    executor.insert_external_event("rl_action", action, scheduled_time=0.0)
    executor.step(float(next_tick))


def test_rl_surface_ship_reuses_existing_domain_models() -> None:
    _executor, context, ship = _build_graph()

    assert isinstance(ship.manuever, Manuever)
    assert isinstance(ship.launcher, Launcher)
    assert ship.retrieve_input_ports() == ["start", "rl_action"]
    assert set(ship.get_models().values()) == {
        ship.rl_controller,
        ship.launcher,
    }
    assert context.items == [ship.mo]
    assert ship.get_position() == (0.0, 0.0, 0.0)


def test_six_actions_apply_at_relative_due_now_boundaries_and_launch_once() -> None:
    executor, context, ship = _build_graph()
    observed_headings = []

    for action in range(6):
        _step_action(executor, context, action)
        observed_headings.append(ship.mo.heading)

    assert ACTION_COMMANDS == (
        (0.0, False),
        (-45.0, False),
        (45.0, False),
        (0.0, True),
        (-45.0, True),
        (45.0, True),
    )
    assert ship.rl_controller.action_times == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert executor.get_global_time() == 6.0
    assert observed_headings == [0.0, 315.0, 0.0, 0.0, 315.0, 0.0]
    assert ship.rl_controller.effective_launches == 1
    assert ship.launcher.launch_flag is True
    assert len(context.decoys) == 4
    assert ship.rl_controller.action_mask == (
        True,
        True,
        True,
        False,
        False,
        False,
    )
    assert math.isfinite(ship.get_position()[0])
    assert ship.get_position() != (0.0, 0.0, 0.0)


@pytest.mark.parametrize("action", [True, False, -1, 6, 1.5, "1", None])
def test_action_decoder_rejects_values_outside_the_closed_integer_space(
    action: object,
) -> None:
    expected = TypeError if isinstance(action, (bool, float, str)) or action is None else ValueError
    with pytest.raises(expected):
        decode_action(action)
