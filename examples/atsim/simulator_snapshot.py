import project_config

from pyjevsim import SysExecutor, ExecutionType, Infinite
from model.manuever import Manuever
from model.surfaceship import SurfaceShip
from utils.scenario_manager import ScenarioManager
from utils.pos_plotter import PositionPlotter
from utils.object_db import ObjectDB


class BankGenModelCondition(SnapshotCondition) :
    @staticmethod
    def create_executor(behavior_executor) :
        return BankGenModelCondition(behavior_executor)
    
    def __init__(self, behavior_executor):
        super().__init__(behavior_executor) #set behavior_executor
        self.check = True
        
    def snapshot_time_condition(self, global_time):
        #snapshot model
        if global_time >= 10000 and self.check:
            self.check = False
            return True

pos_plot = PositionPlotter()
#sm = ScenarioManager('./examples/atsim/scenarios/stationary_decoy.yaml')
sm = ScenarioManager('./examples/atsim/scenarios/self_propelled_decoy.yaml')
se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)
ObjectDB().set_executor(se)

se.insert_input_port("start")

for ship in sm.get_surface_ships():
	se.register_entity(ship)
	se.coupling_relation(se, "start", ship, "start")

for torpedo in sm.get_torpedoes():
	se.register_entity(torpedo)
	se.coupling_relation(se, "start", torpedo, "start")
	pass

se.insert_external_event("start", None)

for _ in range(30):
	se.simulate(1)
	for ship in sm.get_surface_ships():
		x, y, z = ship.get_position()
		pos_plot.update_position('ship', x, y, z)

	for torpedo in sm.get_torpedoes():
		x, y, z = torpedo.get_position()
		pos_plot.update_position('torpedo', x, y, z, 'black', 'orange')

	for name, decoy in ObjectDB().decoys:
		x, y, z = decoy.get_position()
		pos_plot.update_position(name, x, y, z, 'black', 'green')

se.terminate_simulation()
