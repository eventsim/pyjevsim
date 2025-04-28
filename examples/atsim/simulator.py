import project_config

from pos_plotter import PositionPlotter
from pyjevsim import SysExecutor, ExecutionType, Infinite
from manuever import Manuever
from manuever_object import ManueverObject


from surfaceship import SurfaceShip

from scenario_manager import ScenarioManager

pos_plot = PositionPlotter()
sm = ScenarioManager('./scenarios/stationary_decoy.yaml')
se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)

se.insert_input_port("start")

for ship in sm.get_surface_ships():
	se.register_entity(ship)
	se.coupling_relation(se, "start", ship, "start")

for torpedo in sm.get_torpedoes():
	se.register_entity(torpedo)
	se.coupling_relation(se, "start", torpedo, "start")

se.insert_external_event("start", None)

with open("output.csv", 'w') as file:
	file.write("id,x,y,z,\n")
	for _ in range(100):
		se.simulate(1)
		for ship in sm.get_surface_ships():
			x, y, z = ship.get_position()
			pos_plot.update_position('ship', x, y, z)
			file.write(f"ship, {x},{y},{z},\n")
		for torpedo in sm.get_torpedoes():
			x, y, z = torpedo.get_position()
			pos_plot.update_position('torpedo', x, y, z, 'black', 'orange')
			file.write(f"torpedo, {x},{y},{z},\n")
	