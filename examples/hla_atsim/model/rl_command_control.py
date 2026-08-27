"""RL command-control atomic model for the deterministic AT/SIM workload.

The model accepts one of the six closed actions declared by IF-RL-014.  A
heading command is applied when the executor delivers the external event.  A
first deploy command schedules a zero-time output to the existing
``Launcher``; subsequent deploy commands are deterministic no-ops.
"""

from __future__ import annotations

from typing import Final

from pyjevsim.system_message import SysMessage

from .manuever import Manuever


ACTION_COMMANDS: Final[tuple[tuple[float, bool], ...]] = (
    (0.0, False),
    (-45.0, False),
    (45.0, False),
    (0.0, True),
    (-45.0, True),
    (45.0, True),
)


def decode_action(action: object) -> tuple[float, bool]:
    """Return ``(heading_delta_degrees, deploy)`` for one closed action."""

    if isinstance(action, bool) or not isinstance(action, int):
        raise TypeError("anti-torpedo action must be an integer")
    if action < 0 or action >= len(ACTION_COMMANDS):
        raise ValueError("anti-torpedo action must be between 0 and 5")
    return ACTION_COMMANDS[action]


class RLCommandControl(Manuever):
    """Extend the existing maneuver atomic with executor-delivered actions."""

    def __init__(self, name: str, platform: object) -> None:
        super().__init__(name, platform)
        self.insert_state("Launch", 0)

        self.insert_input_port("action")
        self.insert_output_port("launch_order")

        self.previous_action: int | None = None
        self.action_times: list[float] = []
        self.launch_committed = False
        self.effective_launches = 0
        self.last_deploy_effective = False

    @property
    def action_mask(self) -> tuple[bool, ...]:
        """Return the six-action availability mask for adapter diagnostics."""

        deploy_available = not self.launch_committed
        return (
            True,
            True,
            True,
            deploy_available,
            deploy_available,
            deploy_available,
        )

    def ext_trans(self, port: str, message: object) -> None:
        """Apply one action delivered through the coupled-model input port."""

        if port == "start":
            super().ext_trans(port, message)
            return
        if port != "action":
            raise ValueError(f"unexpected RL command-control input port: {port}")

        retrieve = getattr(message, "retrieve", None)
        if not callable(retrieve):
            raise TypeError("action message must provide retrieve()")
        payload = retrieve()
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError("action message must contain exactly one payload")

        action = payload[0]
        heading_delta, deploy = decode_action(action)
        motion = getattr(self.platform, "mo")
        heading = (float(motion.heading) + heading_delta) % 360.0
        motion.change_heading(heading)

        self.previous_action = action
        executor = self.platform.ctx.get_executor()
        self.action_times.append(float(executor.get_global_time()))
        self.last_deploy_effective = deploy and not self.launch_committed
        if self.last_deploy_effective:
            self.launch_committed = True
            self.effective_launches += 1
            self._cur_state = "Launch"

    def output(self, deliverer: object) -> object | None:
        """Run existing motion or emit one effective launch order."""

        if self._cur_state == "Launch":
            message = SysMessage(self.get_name(), "launch_order")
            deliverer.insert_message(message)
            return deliverer
        return super().output(deliverer)

    def int_trans(self) -> None:
        """Resume periodic maneuvering after a zero-time launch emission."""

        if self._cur_state == "Launch":
            self._cur_state = "Generate"
            return
        super().int_trans()
