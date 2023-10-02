# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from abc import abstractmethod
from collections import OrderedDict
from .definition import ModelType
from .core_model import CoreModel

class BehaviorModel(CoreModel):
    def __init__(self, _name=""):
        super().__init__(_name, ModelType.BEHAVIORAL)
        self._states = {}

        self.external_transition_map_tuple = {}
        self.external_transition_map_state = {}
        self.internal_transition_map_tuple = {}
        self.internal_transition_map_state = {}
        
        # added by cbchoi 2023.09.26
        self._cancel_reschedule_f = False

        self._cur_state = "" # rename as active_state?

    def insert_state(self, name, deadline="inf"):
        # TODO: Exception Handling
        # TA < 0
        # Duplicated State
        self._states[name] = float(deadline)

    def update_state(self, name, deadline="inf"):
        # TODO: Exception Handling
        # TA < 0
        self._states[name] = float(deadline)

    # added by jylee 2023.09.26
    def cancel_rescheduling(self):
        self._cancel_reschedule_f = True
        
    def init_state(self, state):
        self._cur_state = state
    
    # added by jylee 2023.09.26
    @abstractmethod
    def ext_trans(self, port, msg):
        pass
    
    @abstractmethod
    def int_trans(self):
        pass
    
    @abstractmethod
    def ouput(self):
        pass
    
    def get_cancel_flag(self):
        return self._cancel_reschedule_f
    
    def reset_cancel_flag(self):
        self._cancel_reschedule_f = False
        
    def retrieve_states(self):
        return self._states

    def find_state(self, name):
        return name in self._states

    def insert_external_transition(self, pre_state, event, post_state):
        self.external_transition_map_tuple[(pre_state, event)] = post_state
        if pre_state in self.external_transition_map_state:
            self.external_transition_map_state[pre_state].append(event, post_state)
        else:
            self.external_transition_map_state[pre_state] = [(event, post_state)]

    def retrieve_external_transition(self, pre_state):
        return self.external_transition_map_state[pre_state]

    def retrieve_next_external_state(self, pre_state, event):
        return self.external_transition_map_tuple[(pre_state, event)]

    def find_external_transition(self, pre_state):
        return pre_state in self.external_transition_map_state

    def insert_internal_transition(self, pre_state, event, post_state):
        self.internal_transition_map_tuple[(pre_state, event)] = post_state
        if pre_state in self.internal_transition_map_state:
            self.internal_transition_map_state[pre_state].append(event, post_state)
        else:
            self.internal_transition_map_state[pre_state] = [(event, post_state)]

    def retrieve_internal_transition(self, pre_state):
        return self.internal_transition_map_state[pre_state]

    def retrieve_next_internal_state(self, pre_state, event):
        return self.internal_transition_map_tuple[(pre_state, event)]

    def find_internal_transition(self, pre_state):
        return pre_state in self.internal_transition_map_state

    def serialize(self):
        json_obj = OrderedDict()
        json_obj["name"] = self._name
        json_obj["states"] = self._states
        json_obj["input_ports"] = self.retrieve_input_ports()
        json_obj["output_ports"] = self.retrieve_output_ports()
        json_obj["external_trans"] = self.external_transition_map_state
        json_obj["internal_trans"] = self.internal_transition_map_state
        return json_obj

    def deserialize(self, json):
        self._name = json["name"]
        for key, value in json["states"].items():
            self.insert_state(key, value)

        # Handle In ports
        for port in json["input_ports"]:
            self.insert_input_port(port)

        # Handle out ports
        for port in json["output_ports"]:
            self.insert_output_port(port)

        # Handle External Transition
        for key, value in json["external_trans"].items():
            for ns in value:
                self.insert_external_transition(key, ns[0], ns[1])

        # Handle Internal Transition
        for key, value in json["internal_trans"].items():
            for ns in value:
                self.insert_internal_transition(key, ns[0], ns[1])

