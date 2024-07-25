from pyjevsim.definition import *
from pyjevsim.snapshot_manager import SnapshotManager

from .model_acoountant import BankAccountant

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):   

    snapshot_manager = SnapshotManager(t_resol, ex_mode=execution_mode, name = "banksim", path = "./snapshot")   
    ss = snapshot_manager.get_engine() #Restore a snapshot simulation


    ss.insert_input_port('start')

    ## Adding a new model to an existing simulation
    ## Increase the number of processes
    que = ss.get_model('Queue')
    que.set_proc_num(8)
    for i in (5, 6, 7) :
        account = BankAccountant(f'processor{i}', i)
        ss.register_entity(account)
        
        ss.coupling_relation(que, f'proc{i}', account, 'in')
        ss.coupling_relation(account, 'next', que, 'proc_checked')
    
    
    ss.insert_external_event('start', None)
    
    ## simulation run
    for _ in range(25000):
        print()
        ss.simulate(1)
        
def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    print(capsys)
    