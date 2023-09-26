from .system_executor import SysExecutor
from .definition import SingletonType, Infinite
from threading import Thread

from .termination_manager import TerminationManager

class SystemSimulator(object):
    __metaclass__ = SingletonType
    _engine = {}

    @staticmethod
    def register_engine(sim_name, sim_mode='VIRTUAL_TIME', time_step=1) -> SysExecutor:
        SystemSimulator._engine[sim_name] = SysExecutor(time_step, sim_name, sim_mode)
        return SystemSimulator._engine[sim_name] 

    @staticmethod
    def get_engine_map():
        return SystemSimulator._engine

    @staticmethod
    def get_engine(sim_name):
        return SystemSimulator._engine[sim_name]

    @staticmethod
    def is_terminated(sim_name):
        return SystemSimulator._engine[sim_name].is_terminated()

    @staticmethod
    def is_terminated(sim_name):
        return SystemSimulator._engine[sim_name].is_terminated()
    
    def exec_non_block_simulate(self, sim_list):
        self.thread_list = []
        for sim_name in sim_list:
            sim_inst = SystemSimulator._engine[sim_name]
            p = Thread(target=sim_inst.simulate, args=(Infinite, False), daemon=True)
            self.thread_list.append(p)
            p.start()
            
            #p.join()

    def block(self):
        self.tm = TerminationManager()

        for t in self.thread_list:
            while t.is_alive():
                t.join(1)
    
    def __init__(self):
        pass



