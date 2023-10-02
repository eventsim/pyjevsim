from pyjevsim.system_executor import SysExecutor
from .model_stm import STM
from .model_peg import PEG
from .model_msg_recv import MsgRecv

def execute_simulation():
    # System Simulator Initialization
    se = SysExecutor(1, _sim_mode="VIRTUAL_TIME")
    #se.register_engine("first", "REAL_TIME", 1)
    se.insert_input_port("start")
    #gen = PEG(0, Infinite, "Gen", "first")
    #se.register_entity(gen)

    gen = STM("Gen")
    se.register_entity(gen, inst_t=3)

    peg = PEG("GEN")
    se.register_entity(peg)

    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(se, "start", peg, "start")

    se.insert_external_event("start", None)
    for _ in range(5):
        se.simulate(1)

def test_f(capsys):
    execute_simulation()
    captured = capsys.readouterr()
