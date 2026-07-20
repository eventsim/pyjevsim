from pyjevsim import BehaviorModel


class SelfPropelledDecoy(BehaviorModel):
    def __init__(self, name, platform, ctx):
        BehaviorModel.__init__(self, name)

        self.platform = platform
        self.ctx = ctx

        self.init_state("Maneuver")
        self.insert_state("Maneuver", 1)

        self._last_tick = None

    def ext_trans(self, port, msg):
        pass

    def output(self, msg_deliver):
        # Once-per-tick integration: calc_next_pos and the check_lifespan/
        # check_flight decrements must happen exactly once per tick.
        tick = self.ctx.tick
        if self._last_tick == tick:
            return
        self._last_tick = tick

        self.platform.calc_next_pos(1)
        if not self.platform.check_lifespan(1) and not self.platform.check_flight(1):
            if self.platform in self.ctx.items:
                self.ctx.items.remove(self.platform)
                self.ctx.removed.append(self.platform.sense_id)

    def int_trans(self):
        if self._cur_state == "Maneuver":
            self._cur_state = "Maneuver"
