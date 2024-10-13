"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module includes SysExecutor, a simulation engine that manages models over time. 
"""

import copy
import datetime
import heapq
import math
import threading
import time
from collections import deque

from .core_model import CoreModel
from .default_message_catcher import DefaultMessageCatcher
from .definition import ExecutionType, Infinite, ModelType, SimulationMode
from .executor_factory import ExecutorFactory
from .system_message import SysMessage
from .termination_manager import TerminationManager

class SysExecutor(CoreModel):
    """SysExecutor managing the execution of models in a simulation.(Simulation Engine)"""

    EXTERNAL_SRC = "SRC"
    EXTERNAL_DST = "DST"

    def __init__(self, _time_resolution, _sim_name="default", ex_mode=ExecutionType.V_TIME, snapshot_manager=None):
        """
        Initializes the SysExecutor with time resolution, simulation name, execution mode, and optional snapshot manager.

        Args:
            _time_resolution (float): The time resolution for the simulation
            _sim_name (str, optional): The name of the simulation
            ex_mode (R_TIME or VTIME): The execution mode
            snapshot_manager (ModelSnapshotManager, optional): Manages SnapshotExecutor
        """
        CoreModel.__init__(self, _sim_name, ModelType.UTILITY)
        self.lock = threading.Lock()

        self.global_time = 0
        self.target_time = 0
        self.time_resolution = _time_resolution

        # dictionary for waiting simulation objects
        self.waiting_obj_map = {}
        # dictionary for active simulation objects
        self.active_obj_map = {}

        # dictionary for object to ports
        self.product_port_map = {}
        self.port_map = {}


        self.hierarchical_structure = {}
        self.model_map = {}
        
        self.min_schedule_item = deque()
        self.sim_init_time = datetime.datetime.now()
        self.simulation_mode = SimulationMode.SIMULATION_IDLE

        # External Interface
        self.input_event_queue = []
        self.output_event_queue = deque()

        # TIME Handling
        self.ex_mode = ex_mode
        self.snapshot_manager = snapshot_manager
        
        if snapshot_manager:
            self.exec_factory = snapshot_manager.get_snapshot_factory()
        else:
            self.exec_factory = ExecutorFactory()
        #Factory pattern to convert Model to ModelExecutor
        
        self.dmc = DefaultMessageCatcher("dc")
        #Model for handling uncaught messages
        self.register_entity(self.dmc)
        
    def get_global_time(self):
        """
        Retrieves the current global time.(simulation time)

        Returns:
            float: The current global time
        """
        return self.global_time
    
    '''
    def set_snapshot_manager(self, snapshot_manager):
        """
        Sets the snapshot manager.

        Args:
            snapshot_manager (ModelSnapshotManager): The snapshot manager to set
        """
        self.snapshot_manager = snapshot_manager
    '''
    
    def register_entity(self, entity, inst_t=0, dest_t=Infinite, ename="default"):
        """
        Register simulation entity(Model).

        Args:
            entity (BehaviorModel or StructuralModel): The entity to register
            inst_t (float, optional): Instance creation time
            dest_t (float, optional): Destruction time
            ename (str, optional): SysExecutor name
        """
        sim_obj = self.exec_factory.create_executor(
            self.global_time, inst_t, dest_t, ename, entity
        )
        #if self.snapshot_manager:
        #    if self.snapshot_manager.check_snapshot_executor(entity.get_name()):
        #        sim_obj = self.snapshot_manager.create_snapshot_executor(sim_obj)
        
        self.product_port_map[entity] = sim_obj

        if not sim_obj.get_create_time() in self.waiting_obj_map:
            self.waiting_obj_map[sim_obj.get_create_time()] = []

        self.waiting_obj_map[sim_obj.get_create_time()].append(sim_obj)

        if sim_obj.get_name() in self.model_map:
            self.model_map[sim_obj.get_name()].append(sim_obj)
        else:
            self.model_map[sim_obj.get_name()] = [sim_obj]

    def get_entity(self, model_name):
        """
        Retrieves entities by model name.

        Args:
            model_name (str): The name of the model

        Returns:
            list: List of entities
        """
        if model_name in self.model_map:
            return self.model_map[model_name]
        return []
    
    def get_model(self, name):
        """
        Retrieve Model by name.

        Args:
            name (str): The name of the model

        Returns:
            CoreModel: Model(BehaviorModel or StructuralModel)
        """
        return self.model_map[name][0].get_core_model()

    def remove_entity(self, model_name):
        """
        Removes an entity by model name.

        Args:
            model_name (str): The name of the model
        """
        if model_name in self.model_map:
            self.destory_entity(self.model_map[model_name])
            del self.model_map[model_name]

    def create_entity(self):
        """
        Creates entities that are scheduled for creation.
        """
        if len(self.waiting_obj_map.keys()) != 0:
            key = min(self.waiting_obj_map)
            if key <= self.global_time:
                lst = self.waiting_obj_map[key]
                for obj in lst:
                    self.active_obj_map[obj.get_obj_id()] = obj
                    obj.set_req_time(self.global_time)
                    self.min_schedule_item.append(obj)
                del self.waiting_obj_map[key]

                self.min_schedule_item = sorted(
                    self.min_schedule_item,
                    key=lambda bm: (bm.get_req_time(), bm.get_obj_id()),
                )

    def destory_entity(self, delete_lst):
        """
        Destroys a list of entities.

        Args:
            delete_lst (list): List of entities to delete
        """
        for agent in delete_lst:
            del self.active_obj_map[agent.get_obj_id()]

            port_del_map = {}
            for key, value in self.port_map.items():
                if key[0] == agent:
                    port_del_map[key] = True

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
        """
        Destroys active entities that are scheduled for destruction.
        """
        if len(self.active_obj_map.keys()) != 0:
            delete_lst = []
            for _, agent in self.active_obj_map.items():
                if agent.get_destruct_time() <= self.global_time:
                    delete_lst.append(agent)

            self.destory_entity(delete_lst)

    def coupling_relation(self, src_obj, out_port, dst_obj, in_port):
        """
        Related Model's input/output ports to each other. 
        Related src_obj's output port to dst_obj's input port.

        Args:
            src_obj (BehaviorMdoel or StructuralModel): Model to relate as output ports 
            out_port (str): src_obj's output port
            dst_obj (CoreModel): Model to relate as input ports 
            in_port (str): dst_obj's input port
        """
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

    def get_relation(self):
        """
        Retrieves the current coupling relations.

        Returns:
            dict: The relation map
        """
        relation_map = {}
        for relation in self.port_map.keys():
            result_out_list = [] 
            in_tuple = (relation[0].get_core_model(), relation[1])
            out_list = self.port_map[relation]
            for out in out_list:
                result_out_list.append((out[0].get_core_model(), out[1]))
            relation_map[in_tuple] = result_out_list
        return relation_map
        
    def remove_relation(self, src, out_port, dst, in_port):
        """
        Removes a coupling relation.

        Args:
            src_obj (BehaviorMdoel or StructuralModel): Models that remove relationships as output port
            out_port (str): src_obj's output port
            dst_obj (CoreModel): Models that remove relationships as input port
            in_port (str): dst_obj's input port
        """
        in_tuple = (self.model_map[src][0], out_port)
        found = self.port_map[in_tuple].index((self.model_map[dst][0], in_port))
        del self.port_map[in_tuple][found]
        
        if self.port_map[in_tuple] == []:
            del self.port_map[in_tuple]

    def reset_relation(self):
        """Resets all coupling relations."""
        self.port_map = {}

    def single_output_handling(self, obj, msg):
        """
        Handles a single output message.

        Args:
            obj (BehaviorModel or StructuralModel): Model
            msg (SysMessage): The message
        """
        pair = (obj, msg[1].get_dst())
        if pair not in self.port_map:
            self.port_map[pair] = [
                (self.active_obj_map[self.dmc.get_obj_id()], "uncaught")
            ]

        for port_pair in self.port_map[pair]:
            destination = port_pair
            if destination is None:
                print("Destination Not Found")
                raise AssertionError

            if destination[0] is self:
                self.output_event_queue.append((self.global_time, msg[1].retrieve()))
            else:
                if destination[0].get_obj_id() in self.active_obj_map:
                    destination[0].ext_trans(destination[1], msg[1])
                    destination[0].set_req_time(self.global_time)

    def output_handling(self, obj, msg):
        """
        Handles output messages.

        Args:
            obj (BehaviorModel or StructuralModel): Model
            msg (SysMessage): The message
        """
        if msg is not None:
            if isinstance(msg[1], list):
                for ith_msg in msg[1]:
                    pair = (msg[0], ith_msg)
                    self.single_output_handling(obj, copy.deepcopy(pair))
            else:
                self.single_output_handling(obj, msg)

    def init_sim(self):
        """Initializes the simulation."""
        self.simulation_mode = SimulationMode.SIMULATION_RUNNING

        if self.active_obj_map is None:
            self.global_time = min(self.waiting_obj_map)

        if not self.min_schedule_item:
            for obj in self.active_obj_map.items():
                if obj[1].time_advance() < 0:
                    print("You should give positive real number for the deadline")
                    raise AssertionError

                obj[1].set_req_time(self.global_time)
                self.min_schedule_item.append(obj[1])

    def schedule(self):
        """Schedules the next simulation event."""
        self.create_entity()
        self.handle_external_input_event()
        
        tuple_obj = self.min_schedule_item.popleft()
        before = time.perf_counter()  # Record time before processing
        
        while math.isclose(tuple_obj.get_req_time(), self.global_time, rel_tol=1e-9):
            msg = tuple_obj.output()
            if msg is not None:
                self.output_handling(tuple_obj, (self.global_time, msg))

            tuple_obj.int_trans()
            req_t = tuple_obj.get_req_time()

            tuple_obj.set_req_time(req_t)
            self.min_schedule_item.append(tuple_obj)

            self.min_schedule_item = deque(
                sorted(
                    self.min_schedule_item,
                    key=lambda bm: (bm.get_req_time(), bm.get_obj_id()),
                )
            )

            tuple_obj = self.min_schedule_item.popleft()

        self.min_schedule_item.appendleft(tuple_obj)

        self.global_time += self.time_resolution

        self.destroy_active_entity()

        if self.ex_mode == ExecutionType.R_TIME:
            delta = float(self.time_resolution) - float(before - time.perf_counter())
            if delta > 0:
                time.sleep(delta)

    def simulate(self, _time=Infinite, _tm=True):
        """
        Runs the simulation for a given amount of time.

        Args:
            _time (float): The simulation time
            _tm (bool): Whether to use the termination manager 
        """
        if _tm:
            self.tm = TerminationManager()

        self.target_time = self.global_time + _time

        self.init_sim()

        while self.global_time < self.target_time:
            if not self.waiting_obj_map:
                if (
                    self.min_schedule_item[0].get_req_time() == Infinite
                    and self.ex_mode == "VIRTUAL_TIME"
                ):
                    self.simulation_mode = SimulationMode.SIMULATION_TERMINATED
                    break

            self.schedule()

    def simulation_stop(self):
        """Stops the simulation and resets SysExecutor."""
        self.global_time = 0
        self.target_time = 0
        self.time_resolution = 1

        self.waiting_obj_map = {}
        self.active_obj_map = {}
        self.port_map = {}

        self.min_schedule_item = deque()

        self.sim_init_time = datetime.datetime.now()

        self.dmc = DefaultMessageCatcher("dc")
        self.register_entity(self.dmc)

    def insert_external_event(self, _port, _msg, scheduled_time=0):
        """
        Inserts an external event into the simulation.
        
        Args:
            _port (str): port name
            _msg (SysMessage or None): Event message
            scheduled_time (float, optional): The scheduled time for the event
        """
        sys_msg = SysMessage("SRC", _port)
        sys_msg.insert(_msg)

        if _port in self.external_input_ports:
            with self.lock:
                heapq.heappush(
                    self.input_event_queue, (scheduled_time + self.global_time, sys_msg)
                )
        else:
            print("[INSERT_EXTERNAL_EVNT] Port Not Found")

    def insert_custom_external_event(self, _port, _bodylist, scheduled_time=0):
        """
        Inserts a custom external event into the simulation.

        Args:
            _port (str): The port name / 포트 이름
            _bodylist (list): The list of message bodies
            scheduled_time (float, optional): The scheduled time for the event
        """
        sys_msg = SysMessage("SRC", _port)
        sys_msg.extend(_bodylist)

        if _port in self.external_input_ports:
            with self.lock:
                heapq.heappush(
                    self.input_event_queue, (scheduled_time + self.global_time, sys_msg)
                )
        else:
            print("[INSERT_EXTERNAL_EVNT] Port Not Found")

    def get_generated_event(self):
        """
        Returns the queue of generated events.
        
        Returns:
            deque: The queue of generated events
        """
        return self.output_event_queue

    def handle_external_input_event(self):
        """Handles external input events."""
        event_list = [ev for ev in self.input_event_queue if ev[0] <= self.global_time]
        for event in event_list:
            self.output_handling(self, event)
            with self.lock:
                heapq.heappop(self.input_event_queue)

        self.min_schedule_item = deque(
            sorted(
                self.min_schedule_item,
                key=lambda bm: (bm.get_req_time(), bm.get_obj_id()),
            )
        )

    def handle_external_output_event(self):
        """
        Handles external output events and clears the output event queue.
        
        Returns:
            list: List of output events
        """
        event_lists = copy.deepcopy(self.output_event_queue)
        self.output_event_queue.clear()
        return event_lists

    def is_terminated(self):
        """
        Checks if the simulation is terminated.
        
        Returns:
            bool: True if terminated, False otherwise
        """
        return self.simulation_mode == SimulationMode.SIMULATION_TERMINATED
    
    def snapshot_simulation(self, name = "", directory_path=".") : 
        """
        Snapshot the model and its releases. 

        Args : 
            name(str) : Name of the simulation to be snapshot
            directory_path : Where the simulation will be snapshot
            
        Raises:
            ValueError: Snapshot manager is not set.
        """
        if not self.snapshot_manager : 
            raise ValueError("Snapshot manager is not set. Cannot take snapshot.")
        
        if name == "" :
            name = self.get_name()
        
        self.snapshot_manager.snapshot_simulation(self.port_map, self.model_map, name, directory_path)
        