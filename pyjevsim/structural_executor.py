"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a StructuralExecutor, an object for executing a StructuralModel.
"""

import copy
from collections import deque

from .definition import Infinite
from .executor import Executor

from .executor_factory import ExecutorFactory
from .message_deliverer import MessageDeliverer

class StructuralExecutor(Executor) :
    def __init__(self, global_time, itime, dtime, ename, model, parent, factory):
        """Structural Exeuctor
        
        Args : 
            global_time (float): Global simulation time
            itime (float): Instance creation time 
            dtime (float): Destruction time
            ename (str): SysExecutor name
            model (StructuralModel): StructuralModel to execute
            factory(ExecutorFactory) : 

        """
        super().__init__(itime, dtime, ename, model, parent)
        self.global_time = global_time
        self.ex_factory = factory
        self.behavior_object = model
        
        self.min_schedule_item = []
        self.model_executor_map = {}
        self.sm = model
               
        for model_id, model in self.behavior_object.get_models().items() : 
            executor = factory.create_executor(global_time, itime, dtime, ename, model, self)
            self.min_schedule_item.append((executor.time_advance(), executor))
            self.model_executor_map[model] = executor
            
        self.time_advance()
        
        self.request_time = 0
        self._next_event_t = 0

    def __str__(self):
        return "[N]:{0}, [S]:{1}".format(self.get_name(), "")
        
    def time_advance(self):
        #print(self.__str__())
        self.min_schedule_item = deque(
            sorted(
                self.min_schedule_item,
                key=lambda bm: (bm[1].get_create_time(), bm[1].get_obj_id()),
            )
        )
        return self.min_schedule_item[0][0]  # Return the earliest time_advance
    
    def route_message(self, cr, msg):
        couplings = self.behavior_object.get_couplings().get(cr, [])

        for coupling in couplings:
            if coupling[0] == self.behavior_object:
                msg.set_source(coupling[0])
                msg.set_port(coupling[1])

                msg_deliver = MessageDeliverer()
                msg_deliver.insert_message(msg)
                self.parent.output(msg_deliver)
            else:
                # Handle internal coupling
                dst_executor = self.model_executor_map.get(coupling[0])
                if dst_executor:
                    self.min_schedule_item = [item for item in self.min_schedule_item if item[1] != dst_executor]

                    dst_executor.ext_trans(coupling[1], msg)
                    dst_executor.set_req_time(self.request_time)

                    self.min_schedule_item.append((dst_executor.time_advance(), dst_executor))

    def set_req_time(self, global_time):
        if self.time_advance() >= Infinite:
            self.next_event_time = Infinite
            self.request_time = Infinite
        else:
            self.request_time = global_time + self.time_advance()

    def get_create_time(self):
        self.next_event_time = self.request_time
        return self.request_time
        
    def get_name(self):
        return self.sm.get_name()
    
    def get_destruct_time(self):
        return self._destruct_t

    def get_obj_id(self):
        return self.sm.get_obj_id()


    def get_req_time(self):
        return self.request_time
    
    def ext_trans(self, port, msg):
        print(self.__str__())
        source = self.parent  
        cr = (self.behavior_object, port)  

        if msg.get_src() == source:
            self.route_message(cr, msg)
        else:
            self.route_message(cr, msg)
        
    def int_trans(self):
        # Get the earliest executor from the schedule list
        #print("!!!!!!", self.min_schedule_item)
        self.min_schedule_item = deque(
            sorted(
                self.min_schedule_item,
                key=lambda bm: (bm[1].get_create_time(), bm[1].get_obj_id()),
            )
        )
        time_advance, executor = self.min_schedule_item.popleft()

        # Perform internal transition
        executor.int_trans()
        executor.set_req_time(self.request_time)

        # Update next event time and reinsert into schedule list
        next_event_time = executor.time_advance()
        self.min_schedule_item.append((next_event_time, executor))

    def output(self, msg_deliver):
        print(self.__str__())
        if not msg_deliver.has_contents():
            # Invoke output function of the first executor in schedule list
            self.min_schedule_item = deque(
                sorted(
                    self.min_schedule_item,
                    key=lambda bm: (bm[1].get_create_time(), bm[1].get_obj_id()),
                )
            )
            _, executor = self.min_schedule_item[0]
            executor.output(msg_deliver)

        while msg_deliver.has_contents():
            msg = msg_deliver.get_contents().popleft()
            cr = (msg.get_source(), msg.get_out_port())

            couplings = self.behavior_object.get_couplings().get(cr, [])
            self.route_message(cr, msg)

