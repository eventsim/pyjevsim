"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
"""This module contains a StructuralExecutor, an object for executing a StructuralModel."""

import copy
from collections import deque

from .definition import Infinite
from .executor import Executor


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

    # External Transition
    def ext_trans(self, port, msg):
        print("ext trans :", msg)
        self.output_event_handling(self, msg)
        

    # Internal Transition
    def int_trans(self):
        self.min_schedule_item[0].int_trans()
        

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
