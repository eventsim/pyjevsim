'''
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
'''

from collections import deque
import heapq
import copy
import time
import datetime
import threading
import math

from .definition import ExecutionType, Infinite, ModelType, SimulationMode
from .core_model import CoreModel
from .default_message_catcher import DefaultMessageCatcher
from .system_message import SysMessage

from .termination_manager import TerminationManager
from .executor_factory import ExecutorFactory

class SysExecutor(CoreModel):

    EXTERNAL_SRC = "SRC"
    EXTERNAL_DST = "DST"

    def __init__(self, _time_resolution, _sim_name='default', ex_mode=ExecutionType.V_TIME):
        CoreModel.__init__(self, _sim_name, ModelType.UTILITY)
        self.lock = threading.Lock()
        #self.thread_flag = False

        self.global_time = 0
        self.target_time = 0
        self.time_resolution = _time_resolution  # time_resolution may changed? - cbchoi

        # dictionary for waiting simulation objects
        self.waiting_obj_map = {}
        # dictionary for active simulation objects
        self.active_obj_map = {}

        # dictionary for object to ports
        self.product_port_map = {}
        self.port_map = {}

        # added by cbchoi 2020.01.20
        self.hierarchical_structure = {}

        # added by cbchoi 2022.08.06
        self.model_map = {}

        self.min_schedule_item = deque()

        self.sim_init_time = datetime.datetime.now()

        self.exec_factory = ExecutorFactory()

        self.dmc = DefaultMessageCatcher("dc")
        self.register_entity(self.dmc)

        self.simulation_mode = SimulationMode.SIMULATION_IDLE

        # External Interface
        self.input_event_queue = []
        self.output_event_queue = deque()

        # TIME Handling
        self.ex_mode = ex_mode

    # retrieve global time
    def get_global_time(self):
        return self.global_time


    def register_entity(self, entity, inst_t=0, dest_t=Infinite, ename="default"):
        #sim object에서 behavior executor
        sim_obj = self.exec_factory.create_executor(self.global_time, inst_t, dest_t, ename, entity)
        self.product_port_map[entity] = sim_obj

        if not sim_obj.get_create_time() in self.waiting_obj_map:
            self.waiting_obj_map[sim_obj.get_create_time()] = []

        self.waiting_obj_map[sim_obj.get_create_time()].append(sim_obj)

        # added by cbchoi 2022.08.06
        if sim_obj.get_name() in self.model_map:
            self.model_map[sim_obj.get_name()].append(sim_obj)
        else:
            self.model_map[sim_obj.get_name()] = [sim_obj]

    # added by cbchoi 2022.08.06
    def get_entity(self, model_name):
        if model_name in self.model_map:
            return self.model_map[model_name]
        return []

    def remove_entity(self, model_name):
        if model_name in self.model_map:
            self.destory_entity(self.model_map[model_name])
            del self.model_map[model_name]

    def create_entity(self):
        if len(self.waiting_obj_map.keys()) != 0:
            key = min(self.waiting_obj_map)
            if key <= self.global_time:
                lst = self.waiting_obj_map[key]
                for obj in lst:
                    self.active_obj_map[obj.get_obj_id()] = obj
                    obj.set_req_time(self.global_time)
                    self.min_schedule_item.append(obj)
                del self.waiting_obj_map[key]

                # select object that requested minimum time
                self.min_schedule_item = sorted(self.min_schedule_item, key=lambda bm: (bm.get_req_time(), bm.get_obj_id()))

    def destory_entity(self, delete_lst):
        for agent in delete_lst:
            del(self.active_obj_map[agent.get_obj_id()])
                
            port_del_map = {}
            for key, value in self.port_map.items():
                # Sender
                if key[0] == agent:
                    port_del_map[key] = True
                
                # Receiver
                if value:
                    del_items = []
                    for src_port in value:
                        src, _ = src_port
                        if src == agent:
                            del_items.append(src_port)
                    for item in del_items:
                        value.remove(item)

            for key in port_del_map:
                del self.port_map[key]

            if agent in self.min_schedule_item:
                self.min_schedule_item.remove(agent)

    def destroy_active_entity(self):
        if len(self.active_obj_map.keys()) != 0:
            delete_lst = []
            for _, agent in self.active_obj_map.items():
                if agent.get_destruct_time() <= self.global_time:
                    delete_lst.append(agent)

            self.destory_entity(delete_lst)
            
    def coupling_relation(self, src_obj, out_port, dst_obj, in_port):
        if src_obj and src_obj != self:
            src_obj = self.product_port_map[src_obj]
        else:
            src_obj = self
        
        if dst_obj and dst_obj != self:
            dst_obj = self.product_port_map[dst_obj]
        else:
            dst_obj = self

        if (src_obj, out_port) in self.port_map:
            self.port_map[(src_obj, out_port)].append((dst_obj, in_port))
        else:
            self.port_map[(src_obj, out_port)] = [(dst_obj, in_port)]

    def single_output_handling(self, obj, msg):
        pair = (obj, msg[1].get_dst())
        if pair not in self.port_map:
            self.port_map[pair] = [(self.active_obj_map[self.dmc.get_obj_id()], "uncaught")]

        for port_pair in self.port_map[pair]:
            #print(port_pair)
            destination = port_pair
            if destination is None:
                print("Destination Not Found")
                print(self.port_map)               
                raise AssertionError

            if destination[0] is None:
                self.output_event_queue.append((self.global_time, msg[1].retrieve()))
            else:
                # Receiver Message Handling
                destination[0].ext_trans(destination[1], msg[1])
                # Receiver Scheduling
                destination[0].set_req_time(self.global_time)

    def output_handling(self, obj, msg):
        if msg is not None:
            if isinstance(msg[1], list):
                for ith_msg in msg[1]:
                    pair = (msg[0], ith_msg)
                    self.single_output_handling(obj, copy.deepcopy(pair))
            else:
                self.single_output_handling(obj, msg)

    def init_sim(self):
        self.simulation_mode = SimulationMode.SIMULATION_RUNNING

        # Flattening
        #_del_model = []
        #_del_coupling = []
        #for model_lst in self.waiting_obj_map.values():
        #    for model in model_lst:
        #        pass
                #if model.get_type() == ModelType.STRUCTURAL:
                #    self.flattening(model, _del_model, _del_coupling)

        #for target, _model in _del_model:
        #    if _model in self.waiting_obj_map[target]:
        #        self.waiting_obj_map[target].remove(_model)

        #for target, _model in _del_coupling:
        #    if _model in self.port_map[target]:
        #        self.port_map[target].remove(_model)

        # setup inital time        
        if self.active_obj_map is None:
            self.global_time = min(self.waiting_obj_map)

        # search min_scedule_item after first init_sim call
        if not self.min_schedule_item:
            for obj in self.active_obj_map.items():
                if obj[1].time_advance() < 0: # exception handling for parent instance
                    print("You should give positive real number for the deadline")
                    raise AssertionError

                obj[1].set_req_time(self.global_time)
                self.min_schedule_item.append(obj[1])

    def schedule(self):
        # Agent Creation
        self.create_entity()
        # TODO: consider event handling after time pass
        self.handle_external_input_event()

        tuple_obj = self.min_schedule_item.popleft()
        before = time.perf_counter() # TODO: consider decorator

        while math.isclose(tuple_obj.get_req_time(), self.global_time, rel_tol=1e-9):
            msg = tuple_obj.output()
            if msg is not None: 
                self.output_handling(tuple_obj, (self.global_time, msg))
            
            # Sender Scheduling
            tuple_obj.int_trans()
            req_t = tuple_obj.get_req_time()

            tuple_obj.set_req_time(req_t)
            self.min_schedule_item.append(tuple_obj)

            self.min_schedule_item = deque(sorted(self.min_schedule_item, key=lambda bm: (bm.get_req_time(), bm.get_obj_id())))
            
            tuple_obj = self.min_schedule_item.popleft()

        self.min_schedule_item.appendleft(tuple_obj)

        # update Global Time
        self.global_time += self.time_resolution

        # Agent Deletion
        self.destroy_active_entity()

        after = time.perf_counter()
        if self.ex_mode == ExecutionType.R_TIME: # Realtime Constraints?
            time.sleep(max(float(self.time_resolution) - float(after-before), 0))


    def simulate(self, _time=Infinite, _tm=True):
        if _tm:
            self.tm = TerminationManager()

        # Termination Condition
        self.target_time = self.global_time + _time

        # Get minimum scheduled event
        self.init_sim()

        while self.global_time < self.target_time:
            if not self.waiting_obj_map:
                if self.min_schedule_item[0].get_req_time() == Infinite and self.ex_mode == 'VIRTUAL_TIME' :
                    self.simulation_mode = SimulationMode.SIMULATION_TERMINATED
                    break

            self.schedule()

    def simulation_stop(self):
        # may buggy?
        self.global_time = 0
        self.target_time = 0
        self.time_resolution = 1  # time_resolution may changed? - cbchoi

        # dictionary for waiting simulation objects
        self.waiting_obj_map = {}
        # dictionary for active simulation objects
        self.active_obj_map = {}
        # dictionary for object to ports
        self.port_map = {}

        self.min_schedule_item = deque()

        self.sim_init_time = datetime.datetime.now()

        self.dmc = DefaultMessageCatcher("dc")
        self.register_entity(self.dmc)

    # External Event Handling - by cbchoi
    def insert_external_event(self, _port, _msg, scheduled_time=0):
        sys_msg = SysMessage("SRC", _port)
        sys_msg.insert(_msg)

        if _port in self.external_input_ports:
            with self.lock:
                heapq.heappush(self.input_event_queue, (scheduled_time + self.global_time, sys_msg))
        else:
            # TODO Exception Handling
            print("[INSERT_EXTERNAL_EVNT] Port Not Found")

    def insert_custom_external_event(self, _port, _bodylist, scheduled_time=0):
        sys_msg = SysMessage("SRC", _port)
        sys_msg.extend(_bodylist)

        if _port in self.external_input_ports:
            with self.lock:
                heapq.heappush(self.input_event_queue, (scheduled_time + self.global_time, sys_msg))
        else:
            # TODO Exception Handling
            print("[INSERT_EXTERNAL_EVNT] Port Not Found")

    def get_generated_event(self):
        return self.output_event_queue

    def handle_external_input_event(self):
        event_list = [ev for ev in self.input_event_queue if ev[0] <= self.global_time]
        for event in event_list:
            self.output_handling(self, event)
            with self.lock:
                heapq.heappop(self.input_event_queue)
            
        self.min_schedule_item = deque(sorted(self.min_schedule_item, \
                                     key=lambda bm: (bm.get_req_time(), bm.get_obj_id())))

    def handle_external_output_event(self):
        event_lists = copy.deepcopy(self.output_event_queue)
        self.output_event_queue.clear()
        return event_lists

    def is_terminated(self):
        return self.simulation_mode == SimulationMode.SIMULATION_TERMINATED
