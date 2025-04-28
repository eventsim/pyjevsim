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
        #print(self.__str__())
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
        #print(self.__str__())
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


"""
class StructuralExecutor(Executor):
    def __init__(
        self,
        global_time,
        itime=Infinite,
        dtime=Infinite,
        ename="default",
        structural_model=None,
        creator_f=None,
    ):
        super().__init__(itime, dtime, ename)
        self._next_event_t = 0
        self.request_time = float("inf")

        # 2023.09.30 cbchoi
        self.sm = structural_model
        self.min_schedule_item = deque()
        self.creator_functor = creator_f
        self.product_model_map = {}
        self.model_product_map = {}
        self.global_time = global_time

        self.init_executor()

    def get_core_model(self):
        return self.sm
    
    def get_global_time(self) :
        return self.global_time 
    
    def get_creator_functor(self) :
        return self.creator_functor

    # @abstractmethod
    def init_executor(self):
        for model in self.sm.get_models():
            # differentiate Structural Model and Behavioral Model
            executor = self.creator_functor(
                self.global_time, self._instance_t, self._destruct_t, "subsystem", model
            )
            self.product_model_map[executor] = model
            self.model_product_map[model] = executor
            self.min_schedule_item.append(executor)

        self.min_schedule_item = deque(
            sorted(
                self.min_schedule_item,
                key=lambda bm: (bm.get_req_time(), bm.get_obj_id()),
            )
        )
        self.request_time = self.min_schedule_item[0].get_req_time()
        self._next_event_t = self.request_time

    # def __str__(self):
    #    return "[N]:{0}, [S]:{1}".format(self.get_name(), self._cur_state)

    def get_name(self):
        return self.sm.get_name()

    def get_engine_name(self):
        return self.engine_name

    def set_engine_name(self, engine_name):
        self.engine_name = engine_name

    def get_create_time(self):
        return self._instance_t

    def get_destruct_time(self):
        return self._destruct_t

    def get_obj_id(self):
        return self.sm.get_obj_id()

        

    def message_handling(self, obj, msg):
        #print(self.sm.port_map) ##
        if obj in self.product_model_map:
            pair = (obj.get_core_model(), msg.get_dst())
        else:
            pair = (self.get_core_model(), msg.get_dst())
        
        #print("port map", self.product_model_map)
        #print("pair", pair)
        #print("portmap ", self.sm.port_map)
        if pair in self.sm.port_map:
            for port_pair in self.sm.port_map[pair]:
                destination = port_pair
                if destination is None:
                    print("Destination Not Found")
                    # print(self.port_map)
                    raise AssertionError

                if destination[0] not in self.model_product_map:
                    return msg
                    pass
                    ##self.output_event_queue.append((self.global_time, msg[1].retrieve()))
                else:
                    #print("test : ", self.model_product_map[destination[0]])
                    # Receiver Message Handling
                    self.model_product_map[destination[0]].ext_trans(
                        destination[1], msg
                    )

                    #메세지 도착 여부 확인
                    # Receiver Scheduling
                    # wrong : destination[0].set_req_time(self.global_time + destination[0].time_advance())

                    # print(type(destination[0]))
                    self.model_product_map[destination[0]].set_req_time(
                        self.global_time
                    )
                    #print(self.global_time)
                    return None
                    #두 모델 사이 시간 비교 
        else:
            print("uncaught")
            return None
            pass  # TODO: uncaught Message Handling

    def output_event_handling(self, obj, msg):
        #print("msg : ", msg)
        if msg is not None:
            if isinstance(msg, list):
                print("test : ", msg)
                for ith_msg in msg:
                    return self.message_handling(obj, copy.deepcopy(ith_msg))
            else:
                return self.message_handling(obj, msg)

    # Output Function
    def output(self):
        #print(self.min_schedule_item[0].get_core_model().__dict__)
        msg = self.min_schedule_item[0].output()
        print(self.min_schedule_item)
        if msg is not None:
            return self.output_event_handling(
                self.min_schedule_item[0], msg
            )  ## TODO: Output Handling Bugfix
            #print("self : ", self)
            #return None  # Temporarily
        else:
            #print("self : ", self.get_core_model())
            return None

    def set_req_time(self, global_time):
        self.global_time = global_time
        self.min_schedule_item[0].set_req_time(global_time)
        self.min_schedule_item = deque(
            sorted(
                self.min_schedule_item,
                key=lambda bm: (bm.get_req_time(), bm.get_obj_id()),
            )
        )
        self.request_time = global_time + self.min_schedule_item[0].time_advance()

    def get_req_time(self):
        return self.request_time


            
        # External Transition
    def ext_trans(self, port, msg):
        print("ext trans :", msg)
        self.output_event_handling(self, msg)
        
    # Internal Transition
    def int_trans(self):
        self.min_schedule_item[0].int_trans()
        
    def output_event_handling(self, obj, msg):
        #print("msg : ", msg)
        if msg is not None:
            if isinstance(msg, list):
                print("test : ", msg)
                for ith_msg in msg:
                    return self.message_handling(obj, copy.deepcopy(ith_msg))
            else:
                return self.message_handling(obj, msg)
            
    

    def message_handling(self, obj, msg):
        #print(self.sm.port_map) ##
        if obj in self.product_model_map:
            pair = (obj.get_core_model(), msg.get_dst())
        else:
            pair = (self.get_core_model(), msg.get_dst())
        
        #print("port map", self.product_model_map)
        #print("pair", pair)
        #print("portmap ", self.sm.port_map)
        if pair in self.sm.port_map:
            for port_pair in self.sm.port_map[pair]:
                destination = port_pair
                if destination is None:
                    print("Destination Not Found")
                    # print(self.port_map)
                    raise AssertionError

                if destination[0] not in self.model_product_map:
                    return msg
                    pass
                    ##self.output_event_queue.append((self.global_time, msg[1].retrieve()))
                else:
                    #print("test : ", self.model_product_map[destination[0]])
                    # Receiver Message Handling
                    self.model_product_map[destination[0]].ext_trans(
                        destination[1], msg
                    )

                    #메세지 도착 여부 확인
                    # Receiver Scheduling
                    # wrong : destination[0].set_req_time(self.global_time + destination[0].time_advance())

                    # print(type(destination[0]))
                    self.model_product_map[destination[0]].set_req_time(
                        self.global_time
                    )
                    #print(self.global_time)
                    return None
                    #두 모델 사이 시간 비교 
        else:
            print("uncaught")
            return None
            pass  # TODO: uncaught Message Handling
            
            
    """
