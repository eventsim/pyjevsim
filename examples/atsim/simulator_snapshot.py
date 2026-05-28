import project_config
import sys

from pyjevsim import SysExecutor, ExecutionType, Infinite, SnapshotManager
from model.manuever import Manuever
from model.surfaceship import SurfaceShip
from utils.scenario_manager import ScenarioManager
from utils.pos_plotter import PositionPlotter
from utils.object_db import ObjectDB

# Seconds to pause per frame — controls playback speed (larger = slower).
# Override on the command line, e.g. `python simulator_snapshot.py 2.0`.
FRAME_DELAY = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

pos_plot = PositionPlotter()
#sm = ScenarioManager('./examples/atsim/scenarios/stationary_decoy.yaml')
sm = ScenarioManager('./examples/atsim/scenarios/self_propelled_decoy.yaml')

snapshot_manager = SnapshotManager()

se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager = snapshot_manager)
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

for i in range(30):
	# _tm=False so pyjevsim doesn't install a SIGINT handler that breaks
	# Ctrl+C under the Qt event loop (see simulator.py).
	se.simulate(1, _tm=False)
	if i %3 == 0 :
		se.snapshot_simulation(name = f"atsim{i}", directory_path = "./examples/atsim/snapshot")
   
	for ship in sm.get_surface_ships():
		x, y, z = ship.get_position()
		pos_plot.update_position('ship', x, y, z)

	for torpedo in sm.get_torpedoes():
		x, y, z = torpedo.get_position()
		pos_plot.update_position('torpedo', x, y, z, 'black', 'orange')

	for name, decoy in ObjectDB().decoys:
		x, y, z = decoy.get_position()
		pos_plot.update_position(name, x, y, z, 'black', 'green')

	pos_plot.render(pause=FRAME_DELAY)


se.terminate_simulation()
pos_plot.keep_open()
