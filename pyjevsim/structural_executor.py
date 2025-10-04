"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a StructuralExecutor, an object for executing a StructuralModel.
"""

from .definition import Infinite
from .executor import Executor

from .message_deliverer import MessageDeliverer
from .schedule_queue import ScheduleQueue

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
        
        self.schedule_queue = ScheduleQueue()
        self.model_executor_map = {}
        self.sm = model

        for model_id, model in self.behavior_object.get_models().items() : 
            executor = factory.create_executor(global_time, itime, dtime, ename, model, self)
            self.schedule_queue.push(executor)
            self.model_executor_map[model] = executor

        self.request_time = 0
        self._next_event_t = 0

        # Cache destruct time for performance optimization
        self._cached_destruct_time = self._destruct_t

        self.next_exec_model = self.schedule_queue.pop()
        self.time_advance()

    def __str__(self):
        return "[N]:{0}, [S]:{1}".format(self.get_name(), "")
        
    def get_core_model(self):
        return self.behavior_object

    def time_advance(self):
        return self.next_exec_model.get_req_time()
    
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
                    dst_executor.ext_trans(coupling[1], msg)
                    dst_executor.set_req_time(self.global_time)
                    self.schedule_queue.push(dst_executor)


    def set_req_time(self, global_time):
        self.global_time = global_time
        if self.time_advance() >= Infinite:
            self.next_event_time = Infinite
            self.request_time = Infinite
        else:
            self.request_time = global_time + self.next_exec_model.time_advance()

    def get_create_time(self):
        return self._instance_t
        
    def get_name(self):
        return self.sm.get_name()
    
    def get_destruct_time(self):
        """Returns the destruction time (cached for performance)"""
        return self._cached_destruct_time

    def get_obj_id(self):
        return self.sm.get_obj_id()

    def get_req_time(self):
        self._next_event_t = self.next_exec_model.get_req_time()
        return self._next_event_t
    
    def ext_trans(self, port, msg):
        # EIC handling
        self.route_message((self.behavior_object, port), msg)
        self.next_exec_model = self.schedule_queue.pop()

    def int_trans(self):
        # Perform internal transition
        self.next_exec_model.int_trans()
        #req_t = executor.get_req_time()
        self.next_exec_model.set_req_time(self.global_time)

        # Update next event time and reinsert into schedule list
        self.schedule_queue.push(self.next_exec_model)
        self.next_exec_model = self.schedule_queue.pop()

    def output(self, msg_deliver):
        if not msg_deliver.has_contents():
            # Invoke output function of the first executor in schedule list
            executor = self.next_exec_model
            executor.output(msg_deliver)

        while msg_deliver.has_contents():
            msg = msg_deliver.get_contents().pop()
            cr = (executor.get_core_model(), msg.get_dst())

            self.route_message(cr, msg)
