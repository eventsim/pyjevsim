import project_config

from pyjevsim import SysExecutor, ExecutionType, Infinite
from model.manuever import Manuever
from model.surfaceship import SurfaceShip
from utils.scenario_manager import ScenarioManager
from utils.pos_plotter import PositionPlotter

pos_plot = PositionPlotter()
sm = ScenarioManager('./examples/atsim/scenarios/stationary_decoy.yaml')
se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)

se.insert_input_port("start")

for ship in sm.get_surface_ships():
	se.register_entity(ship)
	se.coupling_relation(se, "start", ship, "start")

for torpedo in sm.get_torpedoes():
	se.register_entity(torpedo)
	se.coupling_relation(se, "start", torpedo, "start")
	pass

se.insert_external_event("start", None)

#with open("output.csv", 'w') as file:
#file.write("id,x,y,z,\n")
for _ in range(20):
	se.simulate(1)
	for ship in sm.get_surface_ships():
		x, y, z = ship.get_position()
		pos_plot.update_position('ship', x, y, z)
		#file.write(f"ship, {x},{y},{z},\n")
	for torpedo in sm.get_torpedoes():
		x, y, z = torpedo.get_position()
		pos_plot.update_position('torpedo', x, y, z, 'black', 'orange')
		#file.write(f"torpedo, {x},{y},{z},\n")

'''
x = 0
y = 0
z = 0
for _ in range(20):
	x = x+1
	y = y+1
	z = z+1
	pos_plot.update_position('ship', x, y, z)
	pos_plot.update_position('torpedo', x+10, y+10, z+10, 'black', 'orange')
'''

se.terminate_simulation()
