"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" This module contains a BehaivorModel object that allows you to implement the Discrete Event System Specification AtomicModel. """

from abc import abstractmethod
from collections import OrderedDict

from .core_model import CoreModel
from .definition import ModelType

class BehaviorModel(CoreModel):
    """BehaviorModel template to inherit when constructing a new Model.

    Args:
        _name (str): Unique model name
    """   
    def __init__(self, _name=""):

        super().__init__(_name, ModelType.BEHAVIORAL)
        self._states = {}

        # External transition map
        self.external_transition_map_tuple = {} 
        self.external_transition_map_state = {}
        
        # Internal transition map
        self.internal_transition_map_tuple = {}
        self.internal_transition_map_state = {}


        self._cancel_reschedule_f = False
        self._cur_state = ""

    def insert_state(self, name, deadline="inf"):
        """
        Insert "state" into the BehaviorModel
        
        Args:
            name (str): State name
            deadline (str or Infinite): Time until the state is active. Defaults to Infinite.
        """
        self._states[name] = float(deadline)

    def update_state(self, name, deadline="inf"):
        """
        Updates an existing state in the BehaviorModel
        
        Args:
            name (str): state name to update
            deadline (str or Infinite): Time until the state is active. Defaults to Infinite.
        """
        self._states[name] = float(deadline)

    def cancel_rescheduling(self):
        """Canceled scheduling"""
        self._cancel_reschedule_f = True
        
        
    def init_state(self, state):
        """
        Sets the initial state
        
        Args:
            state (str): Initial state name
        """
        self._cur_state = state

    def set_global_time(self, gtime):
        """
        Set gloabl time
        
        Args:
            gtime (float): Global time
        """
        self.global_time = gtime 
        pass
    
    @abstractmethod
    def ext_trans(self, port, msg):
        """Defines the external transition, to be implemented by subclasses"""
        pass

    @abstractmethod
    def int_trans(self):
        """Defines the internal transition, to be implemented by subclasses"""
        pass

    @abstractmethod
    def output(self):
        """Defines the output function, to be implemented by subclasses"""
        pass

    def get_cancel_flag(self):
        """Returns the cancel reschedule flag"""
        return self._cancel_reschedule_f

    def reset_cancel_flag(self):
        """Resets the cancel reschedule flag to False"""
        self._cancel_reschedule_f = False

    def retrieve_states(self):
        """Returns the states dictionary"""
        return self._states

    def find_state(self, name):
        """Checks if a state exists
        
        Args:
            name (str): State name
        
        Returns:
            bool: True if state exists, False otherwise
        """
        return name in self._states

    def insert_external_transition(self, pre_state, event, post_state):
        """Inserts an external transition
        
        Args:
            pre_state (str): Previous state
            event (str): Event causing the transition
            post_state (str): Next state
        """
        self.external_transition_map_tuple[(pre_state, event)] = post_state
        if pre_state in self.external_transition_map_state:
            self.external_transition_map_state[pre_state].append((event, post_state))
        else:
            self.external_transition_map_state[pre_state] = [(event, post_state)]

    def retrieve_external_transition(self, pre_state):
        """Retrieves external transitions for a given state
        
        Args:
            pre_state (str): Previous state
        
        Returns:
            list: List of external transitions
        """
        return self.external_transition_map_state[pre_state]

    def retrieve_next_external_state(self, pre_state, event):
        """Retrieves the next state for a given external transition
        
        Args:
            pre_state (str): Previous state
            event (str): Event causing the transition
        
        Returns:
            str: Next state
        """
        return self.external_transition_map_tuple[(pre_state, event)]

    def find_external_transition(self, pre_state):
        """Checks if there are external transitions for a given state
        
        Args:
            pre_state (str): Previous state
        
        Returns:
            bool: True if transitions exist, False otherwise
        """
        return pre_state in self.external_transition_map_state

    def insert_internal_transition(self, pre_state, event, post_state):
        """Inserts an internal transition
        
        Args:
            pre_state (str): Previous state
            event (str): Event causing the transition
            post_state (str): Next state
        """
        self.internal_transition_map_tuple[(pre_state, event)] = post_state
        if pre_state in self.internal_transition_map_state:
            self.internal_transition_map_state[pre_state].append((event, post_state))
        else:
            self.internal_transition_map_state[pre_state] = [(event, post_state)]

    def retrieve_internal_transition(self, pre_state):
        """Retrieves internal transitions for a given state
        
        Args:
            pre_state (str): Previous state
        
        Returns:
            list: List of internal transitions
        """
        return self.internal_transition_map_state[pre_state]

    def retrieve_next_internal_state(self, pre_state, event):
        """Retrieves the next state for a given internal transition
        
        Args:
            pre_state (str): Previous state
            event (str): Event causing the transition
        
        Returns:
            str: Next state
        """
        return self.internal_transition_map_tuple[(pre_state, event)]

    def find_internal_transition(self, pre_state):
        """Checks if there are internal transitions for a given state
        
        Args:
            pre_state (str): Previous state
        
        Returns:
            bool: True if transitions exist, False otherwise
        """
        return pre_state in self.internal_transition_map_state

    def serialize(self):
        """Serializes the behavior model to a JSON object
        
        Returns:
            OrderedDict: Serialized JSON object
        """
        json_obj = OrderedDict()
        json_obj["name"] = self._name
        json_obj["states"] = self._states
        json_obj["input_ports"] = self.retrieve_input_ports()
        json_obj["output_ports"] = self.retrieve_output_ports()
        json_obj["external_trans"] = self.external_transition_map_state
        json_obj["internal_trans"] = self.internal_transition_map_state
        return json_obj

    def deserialize(self, json):
        """Deserializes the behavior model from a JSON object
        
        Args:
            json (dict): JSON object containing the model data
        """
        self._name = json["name"]
        for key, value in json["states"].items():
            self.insert_state(key, value)

        # Handle input ports
        for port in json["input_ports"]:
            self.insert_input_port(port)

        # Handle output ports
        for port in json["output_ports"]:
            self.insert_output_port(port)

        # Handle external transitions
        for key, value in json["external_trans"].items():
            for ns in value:
                self.insert_external_transition(key, ns[0], ns[1])

        # Handle internal transitions
        for key, value in json["internal_trans"].items():
            for ns in value:
                self.insert_internal_transition(key, ns[0], ns[1])