from pyjevsim import BehaviorModel, Infinite


class TrackingManuever(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)

        self.platform = platform

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Manuever", 1)

        self.insert_input_port("start")
        self.insert_input_port("target")

        self.idx = 0
        self._last_tick = None

    def ext_trans(self, port, msg):
        if port == "start":
            self._cur_state = "Manuever"
        # The "target" port is retained for coupling compatibility but is no
        # longer the pursuit path: the target is committed to the physics
        # object at the tick boundary (see utils/ticking.py), so motion is
        # order-independent. Live target messages (which used
        # cancel_rescheduling) reintroduced intra-tick nondeterminism.

    def output(self, msg_deliver):
        # Once-per-tick integration (order-independent).
        tick = self.platform.ctx.tick
        if self._last_tick == tick:
            return
        self._last_tick = tick
        self.idx += 1

        target = getattr(self.platform.mo, "committed_target", None)
        if target is not None:
            self.platform.mo.calc_next_pos_with_pos(target, 1)
        else:
            self.platform.mo.calc_next_pos_with_heading(1)

    def int_trans(self):
        if self._cur_state == "Manuever":
            self._cur_state = "Manuever"
