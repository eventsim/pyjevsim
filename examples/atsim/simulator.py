import project_config

from pyjevsim import SysExecutor, ExecutionType, Infinite
from manuever import Manuever
from manuever_object import ManueverObject
from pos_plotter import PositionPlotter

from surfaceship import SurfaceShip

se = SysExecutor(1, ex_mode=ExecutionType.R_TIME)

se.insert_input_port("start")
gen = Manuever(0, Infinite, "SurfaceShip", "first")
se.register_entity(gen)

se.coupling_relation(se, "start", gen, "start")

se.insert_external_event("start", None)
se.simulate(10)

"""
mo = ManueverObject("mo1", 0, 0, 0, 0, 1, 1)
pos_plot = PositionPlotter()

with open("output.csv", 'w') as file:
	file.write("x,y,z,\n")
	for _ in range(100):
		mo.calc_next_pos_with_pos(10, 10, 10, 1)
		x, y, z = mo.get_position()
		pos_plot.update_position(x, y, z)
		file.write(f"{x},{y},{z},\n")
"""		