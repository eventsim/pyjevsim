from pyjevsim.system_executor import SysExecutor
from .model_stm import STM

def test_f():
    se = SysExecutor(1, _sim_mode="VIRTUAL_TIME")
    se.insert_input_port("start")
 
    gen = STM("Gen")
    se.register_entity(gen, inst_t=3)

    se.coupling_relation(se, "start", gen, "start")
    se.insert_external_event("start", None)
    se.simulate(15)

    gen = se.get_entity("Gen")
    
