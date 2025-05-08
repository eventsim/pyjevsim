import project_config
import yaml


from pyjevsim import SysExecutor, ExecutionType, Infinite, SnapshotManager, RestoreHandler
from model.manuever import Manuever
from model.surfaceship import SurfaceShip
from utils.scenario_manager import ScenarioManager
from utils.pos_plotter import PositionPlotter
from utils.object_db import ObjectDB

pos_plot = PositionPlotter()
#sm = ScenarioManager('./examples/atsim/scenarios/stationary_decoy.yaml')
#sm = ScenarioManager('./examples/atsim/scenarios/self_propelled_decoy.yaml')

with open('./examples/atsim/scenarios/restore_decoys.yaml', 'r') as file:
    decoys_data = yaml.safe_load(file)

snapshot_manager = SnapshotManager(restore_handler=RestoreHandler()) 
    

se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)
#ObjectDB().set_executor(se)

se.insert_input_port("start")


with open(f"./examples/atsim/snapshot/atsim3/blue_ship_0.simx", "rb") as f :
	ship = snapshot_manager.load_snapshot(f"blue_ship_0", f.read()) #restore model

ObjectDB().items.append(ship.mo)

se.register_entity(ship)
se.coupling_relation(se, "start", ship, "start")

with open(f"./examples/atsim/snapshot/atsim3/red_torpedo_0.simx", "rb") as f :
	torpedo = snapshot_manager.load_snapshot(f"red_torpedo_0", f.read()) #restore model
ObjectDB().items.append(torpedo.mo)
se.register_entity(torpedo)
se.coupling_relation(se, "start", torpedo, "start")

decoy_list = []
for i in range(4) :
	#BankUserGenerator Restore
	with open(f"./examples/atsim/snapshot/atsim3/[Decoy][0].simx", "rb") as f :
		de = snapshot_manager.load_snapshot(f"[Decoy][{i}]", f.read()) #restore model
	
	de.platform.set_decoy_info(ship.get_position(), decoys_data["DecoyObjects"][i])
 
	ObjectDB().decoys.append((f"[Decoy][{i}]", de.platform))
	ObjectDB().items.append(de.platform)
	decoy_list.append(de)
	se.register_entity(de)    
   

se.insert_external_event("start", None)

print(se.model_map)

for i in range(30):
	se.simulate(1)
	
	x, y, z = ship.get_position()
	pos_plot.update_position('ship', x, y, z)

	x, y, z = torpedo.get_position()
	pos_plot.update_position('torpedo', x, y, z, 'black', 'orange')

	for name, decoy in ObjectDB().decoys:
		x, y, z = decoy.get_position()
		pos_plot.update_position(name, x, y, z, 'black', 'green')

se.terminate_simulation()
