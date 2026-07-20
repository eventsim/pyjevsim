import math

from pyjevsim import BehaviorModel, Infinite

from .stationary_decoy import StationaryDecoy
from .self_propelled_decoy import SelfPropelledDecoy
from mobject.stationary_decoy_object import StationaryDecoyObject
from mobject.self_propelled_decoy_object import SelfPropelledDecoyObject


class Launcher(BehaviorModel):
    def __init__(self, name, platform):
        BehaviorModel.__init__(self, name)

        self.platform = platform

        self.init_state("Wait")
        self.insert_state("Wait", Infinite)
        self.insert_state("Launch", 0)

        self.insert_input_port("order")

        self.launch_flag = False

    def ext_trans(self, port, msg):
        if port == "order":
            self._cur_state = "Launch"

    def output(self, msg_deliver):
        if not self.launch_flag:
            ctx = self.platform.ctx
            se = ctx.get_executor()

            # Spawn from the ship's frozen snapshot position (start-of-tick),
            # so the launch site does not depend on whether the ship Manuever
            # fired before or after the Launcher within this tick.
            me = ctx.snapshot.get(self.platform.sense_id)
            spawn_pos = me.get_position() if me is not None else self.platform.get_position()

            for idx, decoy in enumerate(self.platform.lo.get_decoy_list()):
                destroy_t = math.ceil(decoy['lifespan'])
                sid = f"{self.platform.sense_id}::decoy_{idx}"

                if decoy["type"] == "stationary":
                    sdo = StationaryDecoyObject(spawn_pos, decoy)
                    decoy_model = StationaryDecoy(sid, sdo, ctx)
                elif decoy["type"] == "self_propelled":
                    sdo = SelfPropelledDecoyObject(spawn_pos, decoy)
                    decoy_model = SelfPropelledDecoy(sid, sdo, ctx)
                else:
                    continue

                sdo.sense_id = sid
                sdo.kind = "decoy"
                ctx.decoys.append((sid, sdo))
                ctx.items.append(sdo)
                se.register_entity(decoy_model, 0, destroy_t)

        self.launch_flag = True

    def int_trans(self):
        if self._cur_state == "Launch":
            self._cur_state = "Wait"
