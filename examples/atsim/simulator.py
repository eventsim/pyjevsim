import project_config
import sys

from pyjevsim import SysExecutor, ExecutionType, Infinite
from model.manuever import Manuever
from model.surfaceship import SurfaceShip
from utils.scenario_manager import ScenarioManager
from utils.pos_plotter import PositionPlotter
from utils.object_db import ObjectDB

# Seconds to pause per frame — controls playback speed (larger = slower).
# Default 1.0 matches the original real-time pacing (1 sim tick per second)
# but stays GUI-responsive. Override on the command line, e.g.
#   python simulator.py 2.0     # slower, easier to watch
#   python simulator.py 0.2     # faster
FRAME_DELAY = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

pos_plot = PositionPlotter()
#sm = ScenarioManager('./examples/atsim/scenarios/stationary_decoy.yaml')
sm = ScenarioManager('./examples/atsim/scenarios/self_propelled_decoy.yaml')
se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)
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
	# _tm=False: don't let pyjevsim install its own SIGINT handler. It
	# overrides the plotter's SIG_DFL every call and, under Qt, can't
	# run anyway — which is exactly why Ctrl+C used to do nothing.
	se.simulate(1, _tm=False)
	for ship in sm.get_surface_ships():
		x, y, z = ship.get_position()
		pos_plot.update_position('ship', x, y, z)

	for torpedo in sm.get_torpedoes():
		x, y, z = torpedo.get_position()
		pos_plot.update_position('torpedo', x, y, z, 'black', 'orange')

	for name, decoy in ObjectDB().decoys:
		x, y, z = decoy.get_position()
		pos_plot.update_position(name, x, y, z, 'black', 'green')

	# Single repaint per frame; the pause both paces the animation and
	# keeps the Qt window responsive (see PositionPlotter docstring).
	pos_plot.render(pause=FRAME_DELAY)

#print(se.model_map)
se.terminate_simulation()
pos_plot.keep_open()  # keep the window interactive after the run

