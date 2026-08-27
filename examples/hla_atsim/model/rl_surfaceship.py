"""RL-controlled surface-ship coupled model for the AT/SIM workload."""

from __future__ import annotations

from typing import Any

from pyjevsim import StructuralModel

from mobject.launcher_object import LauncherObject
from mobject.manuever_object import ManueverObject

from .launcher import Launcher
from .rl_command_control import RLCommandControl


class RLSurfaceShip(StructuralModel):
    """Reuse AT/SIM motion and launcher models behind one RL action port."""

    def __init__(self, name: str, scenario: dict[str, Any], ctx: object) -> None:
        super().__init__(name)
        self.ctx = ctx
        self.sense_id = name

        self.mo = ManueverObject(**scenario["ManueverObject"])
        self.lo = LauncherObject(**scenario["LauncherObject"])
        self.mo.sense_id = name
        self.mo.kind = "ship"
        ctx.items.append(self.mo)

        self.rl_controller = RLCommandControl(f"[{name}][RLCommandControl]", self)
        self.manuever = self.rl_controller
        self.launcher = Launcher(f"[{name}][Launcher]", self)

        self.register_entity(self.rl_controller)
        self.register_entity(self.launcher)

        self.insert_input_port("start")
        self.insert_input_port("rl_action")

        self.coupling_relation(self, "start", self.rl_controller, "start")
        self.coupling_relation(
            self,
            "rl_action",
            self.rl_controller,
            "action",
        )
        self.coupling_relation(
            self.rl_controller,
            "launch_order",
            self.launcher,
            "order",
        )

    def get_position(self) -> tuple[float, float, float]:
        """Return the live ship position used by existing AT/SIM helpers."""

        return self.mo.get_position()
