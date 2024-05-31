from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor
from pyjevsim.snapshot_manager import SnapshotManager

from .model_acoountant import BankAccountant
from .model_queue import BankQueue
from .model_user_gen import BankUserGenerator

from datetime import datetime

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    result = []
    result.append(datetime.now()) #software start time
    
    snapshot_manager = SnapshotManager(t_resol, ex_mode=execution_mode, name = "banksim", path = "./snapshot")
    ss = snapshot_manager.get_engine()

    ss.insert_input_port('start')
    
    que = ss.get_model('Queue')
    que.set_proc_num(8)
    for i in (5, 6, 7) :
        account = BankAccountant(f'processor{i}', i)
        ss.register_entity(account)
        
        ss.coupling_relation(que, f'proc{i}', account, 'in')
        ss.coupling_relation(account, 'next', que, 'proc_checked')
    
    ss.insert_external_event('start', None)
    
    ## simulation run
    result.append(datetime.now()) #simulation start time

    for _ in range(25000):
        print()
        ss.simulate(1)
    
    result.append(datetime.now()) #simulation finish time
    print("<< Software time : ", result[2]-result[0])
    print("<< Simulation time : ", result[2]-result[1])
    
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    print(capsys)
    