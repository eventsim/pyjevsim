from pyjevsim.definition import *
from pyjevsim.system_executor import SysExecutor

from .model_acoountant import BankAccountant
from .model_queue import BankQueue
from .model_user_gen import BankUserGenerator

def execute_simulation(t_resol=1, execution_mode=ExecutionType.V_TIME):
    ss = SysExecutor(t_resol, ex_mode=execution_mode, snapshot_manager=None)
    
    bq =[]

    queue_size = 10
    for i in range(queue_size):
        bqi = BankQueue(f'[Q{i}]')
        bq.append(bqi)
        ss.register_entity(bqi)	

    for i, v in enumerate(bq):
        if i+1 < len(bq):
            ss.coupling_relation(bq[i], 'ready', bq[i+1], 'check')
            ss.coupling_relation(bq[i], 'out', bq[i+1], 'in')
            ss.coupling_relation(bq[i+1], 'ok', bq[i], 'next') 

    ba = BankAccountant('BankAccountant')
    ss.register_entity(ba)

    ss.insert_input_port('start')

    bug = BankUserGenerator('BankUserGenerator')
    ss.register_entity(bug)

    ss.coupling_relation(None, 'start', bug, 'start')
    ss.coupling_relation(bug, 'user_out', bq[0], 'in')


    ss.coupling_relation(bq[-1], 'out', ba, 'in')
    ss.coupling_relation(bq[-1], 'ready', ba, 'check')
    ss.coupling_relation(ba, 'next', bq[-1], 'next')

    ss.insert_external_event('start', None)

    for i in range(100):
        ss.simulate(1)
        for q in bq:
            print(q)

        print(ba)

def test_casual_order1(capsys):
    execute_simulation(1, ExecutionType.V_TIME)
    #captured = capsys.readouterr()
    print(capsys)